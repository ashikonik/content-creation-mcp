/**
 * Lexical search over the skill and agent corpus.
 *
 * Deliberately no embeddings: the search must be offline, deterministic,
 * and answer in well under a second. The ranking blends idf-weighted token
 * matches, bigram matches, curated promptSignals phrase hits, a tier/source
 * bias, and a distinctive-token coverage requirement.
 */
import type {
  AgentRecord,
  ContentDomain,
  LibraryIndex,
  SearchResult,
  SkillRecord,
} from "./types.js";

const STOPWORDS = new Set([
  "a", "an", "the", "and", "or", "but", "if", "then", "than", "that", "this",
  "these", "those", "is", "are", "was", "were", "be", "been", "being", "to",
  "of", "in", "on", "at", "by", "for", "with", "from", "as", "it", "its",
  "you", "your", "we", "our", "they", "their", "he", "she", "his", "her",
  "do", "does", "did", "will", "would", "can", "could", "should", "may",
  "not", "no", "so", "up", "out", "about", "into", "over", "after", "before",
  "how", "what", "when", "where", "which", "who", "whom", "why", "any",
  "some", "all", "each", "more", "most", "other", "such", "only", "own",
  "same", "very", "just", "now", "also", "how", "make", "use", "using",
  "get", "want", "need", "create", "my", "me", "we've", "i'm",
]);

export function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9+#.\s-]/g, " ")
    .split(/\s+/)
    .map((t) => t.replace(/^[.-]+|[.-]+$/g, ""))
    .filter((t) => t.length > 1 && !STOPWORDS.has(t));
}

function bigrams(tokens: string[]): string[] {
  const out: string[] = [];
  for (let i = 0; i < tokens.length - 1; i++) {
    out.push(`${tokens[i]} ${tokens[i + 1]}`);
  }
  return out;
}

interface Doc {
  id: string;
  kind: "skill" | "agent";
  name: string;
  description: string;
  content_domain: ContentDomain;
  source: "authored" | "vendored";
  prompt_signals: string[];
  tokens: Set<string>;
  bigram_set: Set<string>;
}

function toDoc(
  record: SkillRecord | AgentRecord,
  kind: "skill" | "agent",
): Doc {
  const nameTokens = tokenize(record.name);
  const descTokens = tokenize(record.description);
  const signalTokens = record.prompt_signals.flatMap((p) => tokenize(p));

  const tokens = new Set<string>([
    ...nameTokens,
    ...descTokens,
    ...signalTokens,
  ]);

  // Bigrams are built per field. Concatenating name and description first
  // let a bigram straddle the boundary between them — a skill named
  // "video" with a description beginning "generate images" produced the
  // bigram "video generate", which matched nothing in the query but could
  // match a query that happened to span the same seam.
  const bigramSet = new Set<string>([
    ...bigrams(nameTokens),
    ...bigrams(descTokens),
    ...bigrams(signalTokens),
  ]);

  return {
    id: record.id,
    kind,
    name: record.name,
    description: record.description,
    content_domain: record.content_domain,
    source: record.source,
    prompt_signals: record.prompt_signals,
    tokens,
    bigram_set: bigramSet,
  };
}

/**
 * Build the idf table over a document set. Rare tokens carry more weight
 * than common ones, which is what makes "lip-sync" rank above "video".
 */
function buildIdf(docs: Doc[]): Map<string, number> {
  const df = new Map<string, number>();
  for (const doc of docs) {
    for (const token of doc.tokens) {
      df.set(token, (df.get(token) ?? 0) + 1);
    }
  }

  const n = docs.length || 1;
  const idf = new Map<string, number>();
  for (const [token, count] of df) {
    idf.set(token, Math.log(1 + n / (1 + count)));
  }
  return idf;
}

export interface SearchOptions {
  limit?: number;
  modality?: ContentDomain;
  source?: "authored" | "vendored";
  kind?: "skill" | "agent" | "all";
}

/**
 * Score one document against the query.
 *
 * The coverage threshold is the important part: a document only qualifies if
 * a meaningful share of the query's distinctive tokens matched. Without it,
 * a two-word query returns anything containing either word.
 */
function scoreDoc(
  doc: Doc,
  queryTokens: string[],
  queryBigrams: string[],
  idf: Map<string, number>,
): { score: number; matched: string[] } {
  if (queryTokens.length === 0) {
    return { score: 0, matched: [] };
  }

  let score = 0;
  const matched: string[] = [];
  let weightedHits = 0;
  let maxWeight = 0;

  for (const token of queryTokens) {
    const weight = idf.get(token) ?? 1;
    maxWeight += weight;

    if (doc.tokens.has(token)) {
      weightedHits += weight;
      score += weight * 1.0;
      matched.push(token);
    }
  }

  // Distinctive-token coverage: did we match most of the query's weight?
  const coverage = maxWeight > 0 ? weightedHits / maxWeight : 0;
  if (coverage < 0.35) {
    return { score: 0, matched: [] };
  }

  // Bigram bonus — matching the exact phrase is a stronger signal.
  for (const bg of queryBigrams) {
    if (doc.bigram_set.has(bg)) {
      score += 3.0;
      matched.push(bg);
    }
  }

  // Prompt-signal phrase hits. These are curated, high-precision triggers.
  //
  // The bonus is awarded once per document, on the strength of the best
  // matching phrase, and a phrase matches on whole words rather than on
  // a substring.
  //
  // Awarding it per phrase let a skill with six trigger phrases collect
  // six times the bonus of a skill with one, for the same single
  // matching word: "generate an image" gave the image-CDN skill 15
  // points — one for each of its six phrases, every one of which
  // happened to contain the substring "image" — and it outranked the
  // image-generation skill, whose trigger phrase is literally "generate
  // an image". Matching on word boundaries and awarding the bonus once
  // keeps the signal about the quality of the match rather than the
  // number of phrases a skill happens to declare.
  let phraseBonus = 0;
  for (const signal of doc.prompt_signals) {
    const phraseTokens = tokenize(signal);
    const phraseTokenSet = new Set(phraseTokens);
    for (const token of queryTokens) {
      if (token.length > 2 && phraseTokenSet.has(token)) {
        // More of the query covered by this phrase is a better match.
        const covered = queryTokens.filter((t) =>
          phraseTokenSet.has(t),
        ).length;
        const bonus = 2.5 * (covered / queryTokens.length);
        if (bonus > phraseBonus) phraseBonus = bonus;
        break;
      }
    }
  }
  score += phraseBonus;

  // Name matches are worth more than description matches.
  const nameTokens = new Set(tokenize(doc.name));
  for (const token of queryTokens) {
    if (nameTokens.has(token)) score += 2.0;
  }

  // The authored-over-vendored bias is applied in the sort, not in the
  // score.
  //
  // As a score component it decided the ranking between a skill and an
  // agent that matched identically: the script-editing agent was
  // authored and the script-editing skill vendored, so "edit a script"
  // returned the agent — the thing that consults skills — instead of the
  // skill that does the work. A bias between authored and vendored
  // content of the same kind belongs where it cannot outrank a genuine
  // difference in match quality.

  return { score, matched: [...new Set(matched)] };
}

export function search(
  index: LibraryIndex,
  query: string,
  options: SearchOptions = {},
): SearchResult[] {
  const limit = Math.min(Math.max(options.limit ?? 10, 1), 100);
  const kind = options.kind ?? "all";

  const docs: Doc[] = [];
  if (kind !== "agent") {
    for (const skill of index.skills) docs.push(toDoc(skill, "skill"));
  }
  if (kind !== "skill") {
    for (const agent of index.agents) docs.push(toDoc(agent, "agent"));
  }

  let filtered = docs;
  if (options.modality) {
    filtered = filtered.filter((d) => d.content_domain === options.modality);
  }
  if (options.source) {
    filtered = filtered.filter((d) => d.source === options.source);
  }

  const queryTokens = tokenize(query);
  const queryBigrams = bigrams(queryTokens);
  // The idf table describes the corpus that is actually being ranked. Built
  // from the unfiltered set, the weights described a different population
  // than the one the filters select — a token common across all 83 records
  // but rare within, say, the five audio records scored as if it were
  // distinctive.
  const idf = buildIdf(filtered);

  const results: SearchResult[] = [];
  for (const doc of filtered) {
    const { score, matched } = scoreDoc(
      doc,
      queryTokens,
      queryBigrams,
      idf,
    );
    if (score <= 0) continue;

    results.push({
      id: doc.id,
      kind: doc.kind,
      name: doc.name,
      description: doc.description,
      content_domain: doc.content_domain,
      score: Math.round(score * 1000) / 1000,
      source: doc.source,
      matched_signals: matched.slice(0, 8),
    });
  }

  results.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    // Stable tiebreak: prefer the more specific domain order, then id.
    //
    // A skill is preferred over an agent. A capability query asks "what
    // does this" and the skill is what does it; the agent is the thing
    // that consults the skill, and is a better answer to "who would
    // help me with this".
    if (a.kind !== b.kind) return a.kind === "skill" ? -1 : 1;
    // Authored content is the primary corpus; vendored content still
    // ranks, but loses a tie to authored content of the same kind.
    if (a.source !== b.source) return a.source === "authored" ? -1 : 1;
    return a.id.localeCompare(b.id);
  });

  return results.slice(0, limit);
}
