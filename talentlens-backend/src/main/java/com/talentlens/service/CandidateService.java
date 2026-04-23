package com.talentlens.service;

import com.talentlens.dto.response.CandidateResponse;
import com.talentlens.dto.response.PageResponse;
import com.talentlens.repository.CandidateFilterParams;
import org.springframework.data.domain.Pageable;

public interface CandidateService {
    PageResponse<CandidateResponse> listCandidates(String userId, String searchId, CandidateFilterParams params, Pageable pageable);
    void softDelete(String userId, String searchId, String candidateId);
}
