package com.talentlens.repository;

import com.talentlens.model.Candidate;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;

import java.util.List;

public interface CandidateRepositoryCustom {
    Page<Candidate> findWithFilters(String searchId, CandidateFilterParams params, Pageable pageable);
    List<Candidate> findAllWithFilters(String searchId, CandidateFilterParams params);
}
