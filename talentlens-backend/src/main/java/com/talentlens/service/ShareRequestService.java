package com.talentlens.service;

import com.talentlens.dto.request.CreateShareRequestRequest;
import com.talentlens.dto.response.PageResponse;
import com.talentlens.dto.response.RecruiterResponse;
import com.talentlens.dto.response.SearchSummaryResponse;
import com.talentlens.dto.response.ShareRequestResponse;
import org.springframework.data.domain.Pageable;

public interface ShareRequestService {
    PageResponse<RecruiterResponse> listRecruiters(Pageable pageable);
    PageResponse<SearchSummaryResponse> listRecruiterSearches(String recruiterId, Pageable pageable);
    ShareRequestResponse createRequest(String requesterUserId, CreateShareRequestRequest request);
    PageResponse<ShareRequestResponse> listIncoming(String recruiterUserId, Pageable pageable);
    PageResponse<ShareRequestResponse> listOutgoing(String requesterUserId, Pageable pageable);
    ShareRequestResponse approve(String recruiterUserId, String requestId);
    ShareRequestResponse reject(String recruiterUserId, String requestId);
}