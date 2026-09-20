package com.example.myapplication.ai;

import android.content.Context;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * On-Device Clinical Knowledge Base & Vector Search Engine
 * Loads the 24 pre-computed clinical protocols and 384-dimensional dense vectors from assets/rag_db.json.
 * Executes mathematical cosine similarity vector search on-device.
 */
public class KnowledgeBase {

    public static class ClinicalProtocol {
        public final String title;
        public final String category;
        public final String content;
        public final float[] vector;
        public final List<String> keywords;

        public ClinicalProtocol(String title, String category, String content, float[] vector, List<String> keywords) {
            this.title = title;
            this.category = category;
            this.content = content;
            this.vector = vector;
            this.keywords = keywords != null ? keywords : new ArrayList<>();
        }
    }

    public static class SearchResult {
        public final String title;
        public final String category;
        public final String content;
        public final float score;

        public SearchResult(String title, String category, String content, float score) {
            this.title = title;
            this.category = category;
            this.content = content;
            this.score = score;
        }
    }

    private final List<ClinicalProtocol> protocols = new ArrayList<>();
    private final Map<String, float[]> keywordVectors = new HashMap<>();
    private final Map<String, float[]> tensors = new HashMap<>();
    private final Map<String, long[]> tensorShapes = new HashMap<>();
    private JsonObject hkMetadata = null;
    private boolean isLoaded = false;

    public KnowledgeBase() {}

    /**
     * Initializes knowledge base from Android Context assets.
     * Prioritizes the high-performance HKNT 1.0.4 binary format (.hk),
     * with graceful fallback to rag_db.json.
     */
    public synchronized void loadFromContext(Context context) {
        if (isLoaded || context == null) return;

        // 1. Primary: Load from official HKNT 1.0.4 binary package (.hk)
        try (InputStream is = context.getAssets().open("sentinel_mental_health.hk")) {
            if (loadFromHkStream(is)) {
                return;
            }
        } catch (Exception ignored) {
            // Fall back to JSON
        }

        // 2. Fallback: Load from rag_db.json
        try (InputStream is = context.getAssets().open("rag_db.json")) {
            loadFromStream(is);
        } catch (Exception e) {
            System.err.println("[KnowledgeBase] Could not load from assets: " + e.getMessage());
        }
    }

    /**
     * Parses and loads tensors directly from an HKNT 1.0.4 binary stream.
     */
    public synchronized boolean loadFromHkStream(InputStream is) {
        if (isLoaded || is == null) return isLoaded;
        try {
            java.io.ByteArrayOutputStream baos = new java.io.ByteArrayOutputStream();
            byte[] buffer = new byte[8192];
            int n;
            while ((n = is.read(buffer)) != -1) {
                baos.write(buffer, 0, n);
            }
            byte[] data = baos.toByteArray();
            if (data.length < 128) return false;

            java.nio.ByteBuffer bb = java.nio.ByteBuffer.wrap(data).order(java.nio.ByteOrder.LITTLE_ENDIAN);
            byte[] magicBytes = new byte[4];
            bb.get(magicBytes);
            String magic = new String(magicBytes, StandardCharsets.US_ASCII);
            if (!"HKNT".equals(magic)) {
                return false;
            }

            short verMaj = bb.getShort();
            short verMin = bb.getShort();
            int flags = bb.getInt();
            short align = bb.getShort();
            short splitIdx = bb.getShort();
            long tCount = bb.getLong();
            long kvCount = bb.getLong();
            long metaOff = bb.getLong();
            long metaSize = bb.getLong();
            long tocOff = bb.getLong();
            long tocSize = bb.getLong();
            long dataOff = bb.getLong();

            if (metaOff <= 0 || metaSize <= 0 || metaOff + metaSize > data.length) {
                return false;
            }

            String metaJson = new String(data, (int) metaOff, (int) metaSize, StandardCharsets.UTF_8);
            JsonObject root = new JsonParser().parse(metaJson).getAsJsonObject();
            this.hkMetadata = root;

            // Parse Table of Contents (TOC) for all tensors
            tensors.clear();
            tensorShapes.clear();
            if (tocOff > 0 && tCount > 0 && tocOff + tocSize <= data.length) {
                bb.position((int) tocOff);
                for (int t = 0; t < tCount; t++) {
                    int nameLen = bb.getShort() & 0xFFFF;
                    byte[] nameBytes = new byte[nameLen];
                    bb.get(nameBytes);
                    String tensorName = new String(nameBytes, StandardCharsets.UTF_8);
                    int dtVal = bb.get() & 0xFF;
                    int ndim = bb.get() & 0xFF;
                    long[] shape = new long[ndim];
                    int totalElements = 1;
                    for (int d = 0; d < ndim; d++) {
                        shape[d] = bb.getLong();
                        totalElements *= (int) shape[d];
                    }
                    long offset = bb.getLong();
                    long length = bb.getLong();

                    if (dtVal == 0x00 && offset + length <= data.length) {
                        float[] tensorData = new float[totalElements];
                        int savedPos = bb.position();
                        bb.position((int) offset);
                        for (int e = 0; e < totalElements; e++) {
                            tensorData[e] = bb.getFloat();
                        }
                        bb.position(savedPos);
                        tensors.put(tensorName, tensorData);
                        tensorShapes.put(tensorName, shape);
                    }
                }
            }

            JsonArray docs = root.has("documents") ? root.getAsJsonArray("documents") : null;
            if (docs == null || docs.size() == 0) return false;

            int numDocs = docs.size();
            int dim = root.has("embedding_dim") ? root.get("embedding_dim").getAsInt() : 384;

            protocols.clear();
            keywordVectors.clear();

            float[] embeddingsTensor = tensors.get("embeddings");

            for (int i = 0; i < numDocs; i++) {
                JsonObject doc = docs.get(i).getAsJsonObject();
                String title = doc.has("title") ? doc.get("title").getAsString() : "Clinical Protocol";
                String category = doc.has("category") ? doc.get("category").getAsString() : "General";
                String content = doc.has("content") ? doc.get("content").getAsString() : "";

                float[] vec = new float[dim];
                if (embeddingsTensor != null && (i + 1) * dim <= embeddingsTensor.length) {
                    System.arraycopy(embeddingsTensor, i * dim, vec, 0, dim);
                } else {
                    int tensorByteOffset = (int) dataOff + (i * dim * 4);
                    if (tensorByteOffset + (dim * 4) <= data.length) {
                        for (int d = 0; d < dim; d++) {
                            vec[d] = bb.getFloat(tensorByteOffset + (d * 4));
                        }
                    }
                }

                List<String> keywords = new ArrayList<>();
                for (String tw : title.toLowerCase().split("[^a-zA-Z0-9]+")) {
                    if (tw.length() > 2) {
                        keywords.add(tw);
                        if (!keywordVectors.containsKey(tw)) {
                            keywordVectors.put(tw, vec);
                        }
                    }
                }

                protocols.add(new ClinicalProtocol(title, category, content, vec, keywords));
            }

            isLoaded = true;
            System.out.println("[KnowledgeBase] Loaded " + protocols.size() + " clinical protocols and " +
                    tensors.size() + " multimodal tensors from HKNT 1.0.4 binary package.");
            return true;
        } catch (Exception e) {
            System.err.println("[KnowledgeBase] Error parsing HKNT stream: " + e.getMessage());
            return false;
        }
    }

    /**
     * Initializes knowledge base directly from an InputStream.
     */
    public synchronized void loadFromStream(InputStream is) {
        if (isLoaded || is == null) return;
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(is, StandardCharsets.UTF_8))) {
            JsonArray arr = new JsonParser().parse(reader).getAsJsonArray();
            for (int i = 0; i < arr.size(); i++) {
                JsonObject obj = arr.get(i).getAsJsonObject();
                String title = obj.has("title") ? obj.get("title").getAsString() : "Clinical Protocol";
                String category = obj.has("category") ? obj.get("category").getAsString() : "general";
                String content = obj.has("content") ? obj.get("content").getAsString() : "";

                JsonArray vecArr = obj.has("vector") && !obj.get("vector").isJsonNull() ? obj.getAsJsonArray("vector") : null;
                float[] vec = null;
                if (vecArr != null && vecArr.size() > 0) {
                    vec = new float[vecArr.size()];
                    for (int j = 0; j < vecArr.size(); j++) {
                        vec[j] = vecArr.get(j).getAsFloat();
                    }
                }

                JsonArray kwArr = obj.has("keywords") && !obj.get("keywords").isJsonNull() ? obj.getAsJsonArray("keywords") : null;
                List<String> keywords = new ArrayList<>();
                if (kwArr != null) {
                    for (int k = 0; k < kwArr.size(); k++) {
                        String kw = kwArr.get(k).getAsString().toLowerCase();
                        keywords.add(kw);
                        if (vec != null && !keywordVectors.containsKey(kw)) {
                            keywordVectors.put(kw, vec);
                        }
                    }
                }
                for (String tw : title.toLowerCase().split("[^a-zA-Z0-9]+")) {
                    if (tw.length() > 2) {
                        keywords.add(tw);
                        if (vec != null && !keywordVectors.containsKey(tw)) {
                            keywordVectors.put(tw, vec);
                        }
                    }
                }

                protocols.add(new ClinicalProtocol(title, category, content, vec, keywords));
            }
            isLoaded = true;
            System.out.println("[KnowledgeBase] Loaded " + protocols.size() + " clinical protocols successfully.");
        } catch (Exception e) {
            System.err.println("[KnowledgeBase] Error parsing rag_db.json: " + e.getMessage());
        }
    }

    public boolean isLoaded() {
        return isLoaded;
    }

    public int getProtocolCount() {
        return protocols.size();
    }

    /**
     * Computes cosine similarity: (u . v) / (||u|| * ||v||)
     */
    public static float cosineSimilarity(float[] u, float[] v) {
        if (u == null || v == null || u.length != v.length) return 0.0f;
        double dot = 0.0;
        double normU = 0.0;
        double normV = 0.0;
        for (int i = 0; i < u.length; i++) {
            dot += u[i] * v[i];
            normU += u[i] * u[i];
            normV += v[i] * v[i];
        }
        if (normU <= 0.0 || normV <= 0.0) return 0.0f;
        return (float) (dot / (Math.sqrt(normU) * Math.sqrt(normV)));
    }

    /**
     * Synthesizes query embedding from constituent keyword vectors in the semantic space.
     */
    public float[] embedQuery(String query) {
        if (query == null) return null;
        String[] tokens = query.toLowerCase().split("[^a-zA-Z0-9_-]+");
        float[] sumVec = new float[384];
        int count = 0;

        for (String t : tokens) {
            if (keywordVectors.containsKey(t)) {
                float[] kv = keywordVectors.get(t);
                for (int i = 0; i < sumVec.length && i < kv.length; i++) {
                    sumVec[i] += kv[i];
                }
                count++;
            }
        }

        if (count == 0) return null;

        // Normalize
        double norm = 0.0;
        for (float v : sumVec) norm += v * v;
        norm = Math.sqrt(norm);
        if (norm > 0) {
            for (int i = 0; i < sumVec.length; i++) sumVec[i] /= norm;
        }
        return sumVec;
    }

    /**
     * Vector search with cosine similarity and keyword overlap fallback.
     */
    public SearchResult search(String query, float threshold, int maxLength) {
        if (protocols.isEmpty() || query == null || query.trim().isEmpty()) {
            return null;
        }

        float[] queryVec = embedQuery(query);
        String lowerQuery = query.toLowerCase();
        Set<String> queryWords = new HashSet<>();
        for (String w : lowerQuery.split("[^a-zA-Z0-9]+")) {
            if (w.length() > 2) queryWords.add(w);
        }

        ClinicalProtocol bestProtocol = null;
        float bestScore = -1.0f;

        for (ClinicalProtocol p : protocols) {
            float score = 0.0f;

            // 1. Vector cosine similarity if query vector synthesized
            if (queryVec != null && p.vector != null) {
                float vecSim = cosineSimilarity(queryVec, p.vector);
                score = Math.max(score, vecSim);
            }

            // 2. Lexical keyword / title overlap
            int kwMatches = 0;
            for (String kw : p.keywords) {
                if (lowerQuery.contains(kw)) kwMatches++;
            }

            int titleMatches = 0;
            for (String tw : p.title.toLowerCase().split("[^a-zA-Z0-9]+")) {
                if (queryWords.contains(tw)) titleMatches++;
            }

            float lexicalScore = (titleMatches * 0.40f) + Math.min(kwMatches * 0.15f, 0.50f);
            if (queryVec != null && p.vector != null && score > 0.15f) {
                score = (score * 0.60f) + (lexicalScore * 0.40f);
            } else {
                score = Math.max(score, lexicalScore);
            }

            if (score > bestScore) {
                bestScore = score;
                bestProtocol = p;
            }
        }

        if (bestProtocol != null && bestScore >= threshold) {
            String cleanContent = bestProtocol.content;
            if (cleanContent.startsWith("---")) {
                String[] parts = cleanContent.split("---", 3);
                if (parts.length >= 3) {
                    cleanContent = parts[2].trim();
                }
            }
            String snippet = cleanContent.length() > maxLength
                    ? cleanContent.substring(0, maxLength) + "..."
                    : cleanContent;

            return new SearchResult(bestProtocol.title, bestProtocol.category, snippet, Math.round(bestScore * 1000.0f) / 1000.0f);
        }

        return null;
    }

    public SearchResult findMostRelevant(String query) {
        SearchResult res = search(query, 0.30f, 400);
        if (res == null) {
            res = search(query, 0.15f, 400);
        }
        return res;
    }

    public synchronized float[] getTensor(String name) {
        return tensors.get(name);
    }

    public synchronized long[] getTensorShape(String name) {
        return tensorShapes.get(name);
    }

    public synchronized boolean hasTensor(String name) {
        return tensors.containsKey(name);
    }

    public synchronized JsonObject getHkMetadata() {
        return hkMetadata;
    }
}
