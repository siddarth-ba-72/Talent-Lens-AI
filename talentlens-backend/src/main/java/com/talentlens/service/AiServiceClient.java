package com.talentlens.service;

import com.talentlens.dto.ai.SourcingRequestPayload;
import com.talentlens.dto.ai.SourcingResultPayload;
import com.talentlens.model.embedded.ParsedJd;
import org.springframework.web.multipart.MultipartFile;

public interface AiServiceClient {
    ParsedJd parseJd(String jdText);
    ParsedJd parseJdFromFile(MultipartFile file);
    SourcingResultPayload sourceCandidates(SourcingRequestPayload payload);
}
