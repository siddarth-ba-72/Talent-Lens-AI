package com.talentlens.dto.response;

import java.time.Instant;

public record ShareRequestResponse(
        String id,
        String searchId,
        String requesterUserId,
        String ownerUserId,
        String status,
        Instant requestedAt,
        Instant resolvedAt,
        String resolvedBy,
        String note
) {}