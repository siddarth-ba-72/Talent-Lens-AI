package com.talentlens.service;

import com.talentlens.dto.request.SourcingRequest;
import com.talentlens.dto.response.SourcingStatusResponse;

public interface SourcingService {
    SourcingStatusResponse triggerSourcing(String userId, String searchId, SourcingRequest request);
    SourcingStatusResponse getStatus(String userId, String searchId);
}
