package com.talentlens.service;

import com.talentlens.dto.response.PageResponse;
import com.talentlens.dto.response.SearchResponse;
import com.talentlens.dto.response.SearchSummaryResponse;
import com.talentlens.model.Role;
import com.talentlens.repository.SearchFilterParams;
import org.springframework.data.domain.Pageable;
import org.springframework.web.multipart.MultipartFile;

public interface SearchService {
    SearchResponse createSearch(String userId, MultipartFile jdFile, String jdText);
    PageResponse<SearchSummaryResponse> listSearches(String userId, Role role, SearchFilterParams params, Pageable pageable);
    SearchResponse getSearch(String userId, Role role, String searchId);
    void deleteSearch(String userId, String searchId);
}
