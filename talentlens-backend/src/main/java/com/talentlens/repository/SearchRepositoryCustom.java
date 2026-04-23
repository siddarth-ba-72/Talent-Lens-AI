package com.talentlens.repository;

import com.talentlens.model.Search;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;

public interface SearchRepositoryCustom {
    Page<Search> findWithFilters(String userId, boolean isHiringManager, SearchFilterParams params, Pageable pageable);
    void addSharedUserAtomically(String searchId, String userId);
}
