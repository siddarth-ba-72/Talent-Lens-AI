package com.talentlens.service;

import com.talentlens.dto.request.SourcingRequest;
import com.talentlens.dto.response.SourcingStatusResponse;
import com.talentlens.kafka.dto.SourcingResultMessage;

public interface SourcingService {
    SourcingStatusResponse triggerSourcing(String userId, String searchId, SourcingRequest request);
    SourcingStatusResponse getStatus(String userId, String searchId);
    void processSourcingResult(SourcingResultMessage message);
}
