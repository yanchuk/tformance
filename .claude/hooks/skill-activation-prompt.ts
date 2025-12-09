#!/usr/bin/env node
import { readFileSync } from 'fs';
import { join } from 'path';

interface HookInput {
    session_id: string;
    transcript_path: string;
    cwd: string;
    permission_mode: string;
    prompt: string;
}

interface PromptTriggers {
    keywords?: string[];
    intentPatterns?: string[];
}

interface FileTriggers {
    pathPatterns?: string[];
    pathExclusions?: string[];
    contentPatterns?: string[];
}

interface SkillRule {
    type: 'guardrail' | 'domain';
    enforcement: 'block' | 'suggest' | 'warn';
    priority: 'critical' | 'high' | 'medium' | 'low';
    description?: string;
    promptTriggers?: PromptTriggers;
    fileTriggers?: FileTriggers;
}

interface SkillRules {
    version: string;
    description?: string;
    skills: Record<string, SkillRule>;
}

interface MatchedSkill {
    name: string;
    matchType: 'keyword' | 'intent';
    config: SkillRule;
}

async function main() {
    try {
        // Read input from stdin
        const input = readFileSync(0, 'utf-8');
        const data: HookInput = JSON.parse(input);
        const prompt = data.prompt.toLowerCase();

        // Load skill rules
        const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd();
        const rulesPath = join(projectDir, '.claude', 'skills', 'skill-rules.json');

        let rules: SkillRules;
        try {
            rules = JSON.parse(readFileSync(rulesPath, 'utf-8'));
        } catch {
            // No skill-rules.json found, exit silently
            process.exit(0);
        }

        const matchedSkills: MatchedSkill[] = [];

        // Check each skill for matches
        for (const [skillName, config] of Object.entries(rules.skills)) {
            const triggers = config.promptTriggers;
            if (!triggers) {
                continue;
            }

            // Keyword matching
            if (triggers.keywords) {
                const keywordMatch = triggers.keywords.some(kw =>
                    prompt.includes(kw.toLowerCase())
                );
                if (keywordMatch) {
                    matchedSkills.push({ name: skillName, matchType: 'keyword', config });
                    continue;
                }
            }

            // Intent pattern matching
            if (triggers.intentPatterns) {
                const intentMatch = triggers.intentPatterns.some(pattern => {
                    const regex = new RegExp(pattern, 'i');
                    return regex.test(prompt);
                });
                if (intentMatch) {
                    matchedSkills.push({ name: skillName, matchType: 'intent', config });
                }
            }
        }

        // Generate output if matches found
        if (matchedSkills.length > 0) {
            let output = '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n';
            output += '🎯 SKILL ACTIVATION CHECK\n';
            output += '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n';

            // Group by priority
            const critical = matchedSkills.filter(s => s.config.priority === 'critical');
            const high = matchedSkills.filter(s => s.config.priority === 'high');
            const medium = matchedSkills.filter(s => s.config.priority === 'medium');
            const low = matchedSkills.filter(s => s.config.priority === 'low');

            if (critical.length > 0) {
                output += '⚠️ CRITICAL SKILLS (REQUIRED):\n';
                critical.forEach(s => {
                    output += `  → ${s.name}`;
                    if (s.config.description) {
                        output += ` - ${s.config.description}`;
                    }
                    output += '\n';
                });
                output += '\n';
            }

            if (high.length > 0) {
                output += '📚 RECOMMENDED SKILLS:\n';
                high.forEach(s => {
                    output += `  → ${s.name}`;
                    if (s.config.description) {
                        output += ` - ${s.config.description}`;
                    }
                    output += '\n';
                });
                output += '\n';
            }

            if (medium.length > 0) {
                output += '💡 SUGGESTED SKILLS:\n';
                medium.forEach(s => {
                    output += `  → ${s.name}`;
                    if (s.config.description) {
                        output += ` - ${s.config.description}`;
                    }
                    output += '\n';
                });
                output += '\n';
            }

            if (low.length > 0) {
                output += '📌 OPTIONAL SKILLS:\n';
                low.forEach(s => {
                    output += `  → ${s.name}`;
                    if (s.config.description) {
                        output += ` - ${s.config.description}`;
                    }
                    output += '\n';
                });
                output += '\n';
            }

            output += 'ACTION: Use Skill tool BEFORE responding\n';
            output += '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n';

            console.log(output);
        }

        process.exit(0);
    } catch (err) {
        // Exit silently on errors to not block the user
        process.exit(0);
    }
}

main().catch(() => {
    process.exit(0);
});
