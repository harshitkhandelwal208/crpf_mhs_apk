package com.example.myapplication;

import com.example.myapplication.models.JournalRequest;
import com.google.gson.Gson;

import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class JournalRequestTest {
    @Test
    public void serializesStableClientRequestIdForIdempotency() {
        JournalRequest request = new JournalRequest(
                "End-of-day reflection",
                "steady",
                "SUBMITTED",
                "request-123"
        );

        String json = new Gson().toJson(request);

        assertEquals("request-123", request.getClientRequestId());
        assertTrue(json.contains("\"client_request_id\":\"request-123\""));
        assertTrue(json.contains("\"content\":\"End-of-day reflection\""));
        assertFalse(json.contains("clientRequestId"));
    }
}
