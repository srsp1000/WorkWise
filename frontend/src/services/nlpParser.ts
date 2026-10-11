/**
 * WorkWise Natural Language Parser
 *
 * Deterministic bilingual (English & Hindi) parser for construction workday instructions.
 * Extracts:
 * - Worker crew size (e.g. "18 workers", "18 majdoor", "crew of 20")
 * - Shift hours (e.g. "shift 6 AM to 6 PM", "subah 6 se shaam 6 baje tak")
 * - Task identifications and durations (e.g. "concrete for 3 hours", "sariya teen ghante")
 * - Unacclimated worker flags and GRAP pollution stages.
 */

import type { TaskCatalogItem, TaskItemInput } from '../types/api';

export interface ParsedWorkday {
  crewSize?: number;
  shiftStart?: number;
  shiftEnd?: number;
  newCrew?: boolean;
  grapStage?: number;
  tasks: TaskItemInput[];
  rawText: string;
  matchedPhrases: string[];
  unmatchedPhrases: string[];
}

// Hindi number word to digit map
const NUMBER_WORDS: Record<string, number> = {
  one: 1, ek: 1, 'एक': 1,
  two: 2, do: 2, 'दो': 2,
  three: 3, teen: 3, tin: 3, 'तीन': 3,
  four: 4, char: 4, chaar: 4, 'चार': 4,
  five: 5, paanch: 5, panch: 5, 'पांच': 5,
  six: 6, chhe: 6, che: 6, chheh: 6, 'छह': 6,
  seven: 7, saat: 7, 'सात': 7,
  eight: 8, aath: 8, 'आठ': 8,
  nine: 9, nau: 9, 'नौ': 9,
  ten: 10, das: 10, 'दस': 10,
  twelve: 12, barah: 12, 'बारह': 12,
  fifteen: 15, pandrah: 15, 'पंद्रह': 15,
  eighteen: 18, atharah: 18, athra: 18, 'अठारह': 18,
  twenty: 20, bees: 20, 'बीस': 20,
  twentyfive: 25, pachis: 25, 'पच्चीस': 25,
  thirty: 30, tees: 30, 'तीस': 30,
};

// Task keyword alias mapping
const TASK_KEYWORD_ALIASES: Record<string, string[]> = {
  concrete: ['concrete', 'rcc', 'chhat dhalai', 'dhalai', 'cement pour', 'pour', 'कंक्रीट', 'ढलाई'],
  rebar: ['rebar', 'sariya', 'saria', 'steel', 'iron work', 'loha', 'reinforcement', 'सरिया'],
  brickwork: ['brickwork', 'brick', 'chunai', 'eent', 'masonry', 'itai', 'चिनाई', 'ईंट'],
  painting: ['painting', 'paint', 'rangai', 'puttai', 'varnish', 'पेंटिंग', 'रंगाई'],
  material_prep: ['material prep', 'prep', 'material', 'samagri', 'mixing', 'preparation', 'सामग्री'],
  excavation: ['excavation', 'digging', 'khudai', 'earthwork', 'trench', 'खुदाई'],
  crane_lift: ['crane lift', 'crane', 'heavy lift', 'hoisting', 'क्रेन'],
  electrical: ['electrical', 'electric', 'bijli', 'wiring', 'cable', 'बिजली'],
  work_at_height: ['work at height', 'height', 'scaffolding', 'unchai', 'paad', 'ऊंचाई'],
};

export function parseNaturalLanguageInput(
  text: string,
  catalog: Record<string, TaskCatalogItem>
): ParsedWorkday {
  const normalized = text.toLowerCase().replace(/[,.:;]/g, ' ');
  const result: ParsedWorkday = {
    rawText: text,
    tasks: [],
    matchedPhrases: [],
    unmatchedPhrases: [],
  };

  // 1. Parse Crew Size
  // Matches: "18 workers", "18 majdoor", "crew of 20", "atharah worker"
  const crewRegex = /(\b\d{1,3}\b|\b[a-z\u0900-\u097F]+\b)\s*(workers?|majdoors?|mazdoor|laborers?|labour|log|aadmi|worker|मजदूर|श्रमिक)/i;
  const crewMatch = normalized.match(crewRegex);
  if (crewMatch) {
    const rawVal = crewMatch[1];
    let num = parseInt(rawVal, 10);
    if (isNaN(num) && NUMBER_WORDS[rawVal]) {
      num = NUMBER_WORDS[rawVal];
    }
    if (!isNaN(num) && num > 0 && num <= 100) {
      result.crewSize = num;
      result.matchedPhrases.push(`Crew Size: ${num} workers`);
    }
  }

  // 2. Parse Shift Hours
  // Matches: "shift 6 to 18", "shift 6 am to 6 pm", "subah 6 se shaam 6"
  const shiftRegex = /(?:shift|samay|timing)?\s*(?:from|subah)?\s*(\d{1,2}|chhe|che|saat|aath)\s*(?:am|baje)?\s*(?:to|se|-)\s*(\d{1,2}|chhe|che|saat|shaam\s*\d{1,2})\s*(?:pm|baje|tak)?/i;
  const shiftMatch = normalized.match(shiftRegex);
  if (shiftMatch) {
    let startVal = parseInt(shiftMatch[1], 10);
    if (isNaN(startVal) && NUMBER_WORDS[shiftMatch[1]]) {
      startVal = NUMBER_WORDS[shiftMatch[1]];
    }
    let endStr = shiftMatch[2].replace('shaam', '').trim();
    let endVal = parseInt(endStr, 10);
    if (isNaN(endVal) && NUMBER_WORDS[endStr]) {
      endVal = NUMBER_WORDS[endStr];
    }
    // If endVal is 6 and context is PM/shaam, convert to 18
    if (endVal <= 12 && (normalized.includes('pm') || normalized.includes('shaam') || endVal <= startVal)) {
      endVal += 12;
    }
    if (!isNaN(startVal) && !isNaN(endVal) && startVal >= 4 && endVal <= 24 && startVal < endVal) {
      result.shiftStart = startVal;
      result.shiftEnd = endVal;
      result.matchedPhrases.push(`Shift Hours: ${startVal}:00 – ${endVal}:00`);
    }
  }

  // 3. Parse Acclimatization Status
  if (
    normalized.includes('unacclimated') ||
    normalized.includes('new crew') ||
    normalized.includes('new workers') ||
    normalized.includes('naye log') ||
    normalized.includes('naye worker')
  ) {
    result.newCrew = true;
    result.matchedPhrases.push('New/Unacclimated Crew Detected');
  }

  // 4. Parse GRAP Pollution Stage
  const grapMatch = normalized.match(/grap\s*(?:stage)?\s*([0-4]|iii|iv|i|ii)/i);
  if (grapMatch) {
    const romanMap: Record<string, number> = { i: 1, ii: 2, iii: 3, iv: 4 };
    const val = grapMatch[1].toLowerCase();
    const stage = romanMap[val] ?? parseInt(val, 10);
    if (!isNaN(stage) && stage >= 0 && stage <= 4) {
      result.grapStage = stage;
      result.matchedPhrases.push(`GRAP Stage ${stage}`);
    }
  }

  // 5. Parse Tasks & Durations
  const detectedTaskIds = new Set<string>();

  for (const [taskId, aliases] of Object.entries(TASK_KEYWORD_ALIASES)) {
    for (const alias of aliases) {
      if (normalized.includes(alias) && !detectedTaskIds.has(taskId)) {
        detectedTaskIds.add(taskId);
        const taskConfig = catalog[taskId];
        let duration = taskConfig ? taskConfig.default_duration_h : 2;

        // Try extracting specific duration near the alias keyword
        // e.g. "concrete for 3 hours", "sariya teen ghante", "3h rebar"
        const durRegex1 = new RegExp(`${alias}\\s*(?:for|ka kaam)?\\s*(\\d{1,2}|ek|do|teen|char|paanch)\\s*(?:hours?|hrs?|ghante?|h|घंटे)?`, 'i');
        const durRegex2 = new RegExp(`(\\d{1,2}|ek|do|teen|char|paanch)\\s*(?:hours?|hrs?|ghante?|h|घंटे)?\\s*(?:of|ka)?\\s*${alias}`, 'i');

        const m1 = normalized.match(durRegex1);
        const m2 = normalized.match(durRegex2);
        const m = m1 || m2;

        if (m && m[1]) {
          const rawDur = m[1];
          let parsedDur = parseInt(rawDur, 10);
          if (isNaN(parsedDur) && NUMBER_WORDS[rawDur]) {
            parsedDur = NUMBER_WORDS[rawDur];
          }
          if (!isNaN(parsedDur) && parsedDur >= 1 && parsedDur <= 10) {
            duration = parsedDur;
          }
        }

        result.tasks.push({
          id: taskId,
          duration_h: duration,
          crew_required: taskConfig ? taskConfig.crew_required : 4,
          depends_on: taskConfig ? taskConfig.depends_on : [],
        });
        result.matchedPhrases.push(`Task: ${taskConfig ? taskConfig.label : taskId} (${duration}h)`);
        break;
      }
    }
  }

  return result;
}
