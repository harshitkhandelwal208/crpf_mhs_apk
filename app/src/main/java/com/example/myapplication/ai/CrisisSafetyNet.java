package com.example.myapplication.ai;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Deterministic Crisis Safety Net
 * Direct regex interceptor guarding personnel safety prior to any text generation or routing.
 */
public class CrisisSafetyNet {

    private static final List<Pattern> CRISIS_PATTERNS = new ArrayList<>();

    static {
        String[] patterns = {
            "\\b(kill|killing|end)\\s+(my)?self\\b",
            "\\bsuicid(e|al)\\b",
            "\\b(don't|do not|wanna|want to)\\s+live\\b",
            "\\bend\\s+it\\s+all\\b",
            "\\bno\\s+reason\\s+to\\s+live\\b",
            "\\bhurt\\s+myself\\b",
            "\\b(end|take)\\s+(my\\s+)?(own\\s+)?life\\b",
            "\\b(cannot|can'?t)\\s+(take|bear|handle)\\s+this\\b",
            "\\bbetter\\s+off\\s+dead\\b",
            "\\bgive\\s+up\\s+on\\s+life\\b",
            "\\bself[- ]?harm\\b",
            "\\bcan'?t\\s+go\\s+on\\b",
            "\\bshoot\\s+myself\\b",
            "\\bwant\\s+to\\s+die\\b",
            "\\bfrag\\s+(him|them|myself)\\b"
        };
        for (String p : patterns) {
            CRISIS_PATTERNS.add(Pattern.compile(p, Pattern.CASE_INSENSITIVE));
        }
    }

    public static boolean isCrisis(String text) {
        if (text == null || text.trim().isEmpty()) return false;
        for (Pattern p : CRISIS_PATTERNS) {
            Matcher m = p.matcher(text);
            if (m.find()) {
                return true;
            }
        }
        return false;
    }

    public static String generateIntervention(String text) {
        return "CRISIS INTERVENTION TRIGGERED: An acute crisis signal was detected. Immediate confidential support is available 24/7. Please connect with the CRPF Medical Officer or call Tele-MANAS (14416) / Kiran Helpline (1800-599-0019).";
    }
}
