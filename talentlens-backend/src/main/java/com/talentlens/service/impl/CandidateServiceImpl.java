package com.talentlens.service.impl;

import com.talentlens.dto.response.CandidateResponse;
import com.talentlens.dto.response.PageResponse;
import com.talentlens.exception.ForbiddenException;
import com.talentlens.exception.ResourceNotFoundException;
import com.talentlens.mapper.CandidateMapper;
import com.talentlens.model.Candidate;
import com.talentlens.model.Search;
import com.talentlens.repository.CandidateFilterParams;
import com.talentlens.repository.CandidateRepository;
import com.talentlens.repository.SearchRepository;
import com.talentlens.service.CandidateService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;

import java.time.Instant;

@Service
@RequiredArgsConstructor
public class CandidateServiceImpl implements CandidateService {

    private final CandidateRepository candidateRepository;
    private final SearchRepository searchRepository;
    private final CandidateMapper candidateMapper;

    @Override
    public PageResponse<CandidateResponse> listCandidates(String userId, String searchId,
                                                           CandidateFilterParams params, Pageable pageable) {
        assertSearchAccess(searchId, userId);
        Page<Candidate> page = candidateRepository.findWithFilters(searchId, params, pageable);
        return PageResponse.from(page.map(candidateMapper::toResponse));
    }

    @Override
    public void softDelete(String userId, String searchId, String candidateId) {
        Search search = assertSearchAccess(searchId, userId);
        if (!search.getUserId().equals(userId)) {
            throw new ForbiddenException("Only the search owner can delete candidates");
        }

        Candidate candidate = candidateRepository.findByIdAndSearchId(candidateId, searchId)
                .orElseThrow(() -> new ResourceNotFoundException("Candidate not found: " + candidateId));

        candidate.setActive(false);
        candidateRepository.save(candidate);
    }

    private Search assertSearchAccess(String searchId, String userId) {
        Search search = searchRepository.findById(searchId)
                .orElseThrow(() -> new ResourceNotFoundException("Search not found: " + searchId));

        boolean isOwner = search.getUserId().equals(userId);
        boolean isShared = search.getSharedWith() != null && search.getSharedWith().contains(userId);

        if (!isOwner && !isShared) {
            throw new ResourceNotFoundException("Search not found: " + searchId);
        }
        return search;
    }
}
