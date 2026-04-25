package com.talentlens.service.impl;

import com.talentlens.dto.response.PageResponse;
import com.talentlens.dto.response.SearchResponse;
import com.talentlens.dto.response.SearchSummaryResponse;
import com.talentlens.exception.ForbiddenException;
import com.talentlens.exception.InvalidFileException;
import com.talentlens.exception.ResourceNotFoundException;
import com.talentlens.mapper.SearchMapper;
import com.talentlens.model.Role;
import com.talentlens.model.Search;
import com.talentlens.model.SourcingStatus;
import com.talentlens.model.embedded.ParsedJd;
import com.talentlens.repository.CandidateRepository;
import com.talentlens.repository.SearchFilterParams;
import com.talentlens.repository.SearchRepository;
import com.talentlens.repository.SourcingTaskRepository;
import com.talentlens.service.AiServiceClient;
import com.talentlens.service.SearchService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;

import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.stream.Stream;

@Service
@RequiredArgsConstructor
public class SearchServiceImpl implements SearchService {

    private static final Set<String> ALLOWED_CONTENT_TYPES = Set.of(
            "text/plain",
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    );

    private final SearchRepository searchRepository;
    private final CandidateRepository candidateRepository;
    private final SourcingTaskRepository sourcingTaskRepository;
    private final AiServiceClient aiServiceClient;
    private final SearchMapper searchMapper;

    @Override
    public SearchResponse createSearch(String userId, MultipartFile jdFile, String jdText) {
        ParsedJd parsedJd;

        if (jdFile != null && !jdFile.isEmpty()) {
            validateFile(jdFile);
            parsedJd = aiServiceClient.parseJdFromFile(jdFile);
        } else if (StringUtils.hasText(jdText)) {
            parsedJd = aiServiceClient.parseJd(jdText);
        } else {
            throw new InvalidFileException("Either jdText or jdFile must be provided");
        }

        String title = deriveTitle(parsedJd);

        Search search = Search.builder()
                .userId(userId)
                .title(title)
                .rawJdText(jdText)
                .jdFileName(jdFile != null ? jdFile.getOriginalFilename() : null)
                .parsedJd(parsedJd)
                .sourcingStatus(SourcingStatus.IDLE)
                .sourcingPlatforms(new ArrayList<>())
                .candidateCount(0)
                .sharedWith(new ArrayList<>())
                .createdAt(Instant.now())
                .updatedAt(Instant.now())
                .build();

        Search saved = searchRepository.save(search);
        return searchMapper.toResponse(saved);
    }

    @Override
    public PageResponse<SearchSummaryResponse> listSearches(String userId, Role role, SearchFilterParams params, Pageable pageable) {
        boolean isHiringManager = role == Role.HIRING_MANAGER;
        Page<Search> page = searchRepository.findWithFilters(userId, isHiringManager, params, pageable);
        return PageResponse.from(page.map(searchMapper::toSummary));
    }

    @Override
    public SearchResponse getSearch(String userId, Role role, String searchId) {
        Search search = searchRepository.findById(searchId)
                .orElseThrow(() -> new ResourceNotFoundException("Search not found: " + searchId));
        assertAccess(search, userId, role);
        return searchMapper.toResponse(search);
    }

    @Override
    public void deleteSearch(String userId, String searchId) {
        Search search = searchRepository.findById(searchId)
                .orElseThrow(() -> new ResourceNotFoundException("Search not found: " + searchId));
        assertOwnership(search, userId);

        candidateRepository.deleteBySearchId(searchId);
        sourcingTaskRepository.deleteBySearchId(searchId);
        searchRepository.deleteById(searchId);
    }

    private void assertOwnership(Search search, String userId) {
        if (!search.getUserId().equals(userId)) {
            throw new ForbiddenException("Access denied");
        }
    }

    private void assertAccess(Search search, String userId, Role role) {
        if (role == Role.HIRING_MANAGER) {
            List<String> shared = search.getSharedWith();
            if (shared == null || !shared.contains(userId)) {
                throw new ResourceNotFoundException("Search not found: " + search.getId());
            }
        } else {
            assertOwnership(search, userId);
        }
    }

    private void validateFile(MultipartFile file) {
        String contentType = file.getContentType();
        if (contentType == null || !ALLOWED_CONTENT_TYPES.contains(contentType)) {
            throw new InvalidFileException("Unsupported file type. Allowed: .txt, .pdf, .docx");
        }
    }

    private static final DateTimeFormatter TITLE_TIMESTAMP_FMT =
            DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss").withZone(ZoneOffset.UTC);

    private String deriveTitle(ParsedJd parsedJd) {
        // Build a short slug from domain + experience level (fall back to "Search" if missing)
        String base = Stream.of(parsedJd.getDomain(), parsedJd.getExperienceLevel())
                .filter(StringUtils::hasText)
                .map(s -> s.trim().replaceAll("[^a-zA-Z0-9]+", "-"))
                .collect(java.util.stream.Collectors.joining("-"));
        if (!StringUtils.hasText(base)) base = "Search";

        String timestamp = TITLE_TIMESTAMP_FMT.format(Instant.now());
        return base + "_" + timestamp;
    }
}
