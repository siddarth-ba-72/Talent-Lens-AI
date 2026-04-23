package com.talentlens.dto.response;

import java.time.Instant;

public record SourcingStatusResponse(
        String taskId,
        String searchId,
        String runId,
        String status,
        int candidatesFound,
        String error,
        Instant startedAt,
        Instant completedAt
) {}
