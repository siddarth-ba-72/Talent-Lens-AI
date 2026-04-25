package com.talentlens.controller;

import com.talentlens.dto.request.CreateSearchRequest;
import com.talentlens.dto.request.SourcingRequest;
import com.talentlens.dto.response.PageResponse;
import com.talentlens.dto.response.SearchResponse;
import com.talentlens.dto.response.SearchSummaryResponse;
import com.talentlens.dto.response.SourcingStatusResponse;
import com.talentlens.model.Role;
import com.talentlens.repository.SearchFilterParams;
import com.talentlens.service.SearchService;
import com.talentlens.service.SourcingService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.time.Instant;

@RestController
@RequestMapping("/api/searches")
@RequiredArgsConstructor
public class SearchController {

    private final SearchService searchService;
    private final SourcingService sourcingService;

    @PostMapping(path = "/jd-file", consumes = {"multipart/form-data"})
    public ResponseEntity<SearchResponse> createSearchFromFile(
            @AuthenticationPrincipal String userId,
            @RequestParam MultipartFile jdFile) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(searchService.createSearch(userId, jdFile, null));
    }

    @PostMapping(path = "/jd-text", consumes = {"application/json"})
    public ResponseEntity<SearchResponse> createSearchFromText(
            @AuthenticationPrincipal String userId,
            @RequestBody CreateSearchRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(searchService.createSearch(userId, null, request.getJdText()));
    }

    @GetMapping
    public ResponseEntity<PageResponse<SearchSummaryResponse>> listSearches(
            @AuthenticationPrincipal String userId,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant dateFrom,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant dateTo,
            @RequestParam(defaultValue = "createdAt") String sortBy,
            @RequestParam(defaultValue = "desc") String sortOrder,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {

        Role role = resolveRole();
        SearchFilterParams params = SearchFilterParams.builder()
                .keyword(keyword)
                .status(status)
                .dateFrom(dateFrom)
                .dateTo(dateTo)
                .build();

        Sort sort = Sort.by("desc".equalsIgnoreCase(sortOrder)
                ? Sort.Direction.DESC : Sort.Direction.ASC, sortBy);
        Pageable pageable = PageRequest.of(page, size, sort);

        return ResponseEntity.ok(searchService.listSearches(userId, role, params, pageable));
    }

    @GetMapping("/{id}")
    public ResponseEntity<SearchResponse> getSearch(
            @AuthenticationPrincipal String userId,
            @PathVariable String id) {
        Role role = resolveRole();
        return ResponseEntity.ok(searchService.getSearch(userId, role, id));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteSearch(
            @AuthenticationPrincipal String userId,
            @PathVariable String id) {
        searchService.deleteSearch(userId, id);
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/{id}/source")
    public ResponseEntity<SourcingStatusResponse> triggerSourcing(
            @AuthenticationPrincipal String userId,
            @PathVariable String id,
            @Valid @RequestBody SourcingRequest request) {
        return ResponseEntity.status(HttpStatus.ACCEPTED)
                .body(sourcingService.triggerSourcing(userId, id, request));
    }

    @GetMapping("/{id}/source-status")
    public ResponseEntity<SourcingStatusResponse> getSourceStatus(
            @AuthenticationPrincipal String userId,
            @PathVariable String id) {
        return ResponseEntity.ok(sourcingService.getStatus(userId, id));
    }

    private Role resolveRole() {
        boolean isRecruiter = SecurityContextHolder.getContext().getAuthentication()
                .getAuthorities().contains(new SimpleGrantedAuthority("ROLE_RECRUITER"));
        return isRecruiter ? Role.RECRUITER : Role.HIRING_MANAGER;
    }
}
