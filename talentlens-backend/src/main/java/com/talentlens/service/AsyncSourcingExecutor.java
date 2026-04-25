package com.talentlens.service;

import com.talentlens.dto.ai.SourcingRequestPayload;

public interface AsyncSourcingExecutor {
    void execute(SourcingRequestPayload payload);
}
