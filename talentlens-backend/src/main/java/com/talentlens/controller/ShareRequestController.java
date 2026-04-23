package com.talentlens.controller;

import com.talentlens.dto.request.CreateShareRequestRequest;
import com.talentlens.dto.response.PageResponse;
import com.talentlens.dto.response.RecruiterResponse;
import com.talentlens.dto.response.ShareRequestResponse;
import com.talentlens.service.ShareRequestService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/share-requests")
@RequiredArgsConstructor
public class ShareRequestController {

    private final ShareRequestService shareRequestService;

    @GetMapping("/recruiters")
    public ResponseEntity<PageResponse<RecruiterResponse>> listRecruiters(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Pageable pageable = PageRequest.of(page, size);
        return ResponseEntity.ok(shareRequestService.listRecruiters(pageable));
    }

    @PostMapping
    public ResponseEntity<ShareRequestResponse> createRequest(
            @AuthenticationPrincipal String userId,
            @Valid @RequestBody CreateShareRequestRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(shareRequestService.createRequest(userId, request));
    }

    @GetMapping("/incoming")
    public ResponseEntity<PageResponse<ShareRequestResponse>> listIncoming(
            @AuthenticationPrincipal String userId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        Pageable pageable = PageRequest.of(page, size);
        return ResponseEntity.ok(shareRequestService.listIncoming(userId, pageable));
    }

    @GetMapping("/outgoing")
    public ResponseEntity<PageResponse<ShareRequestResponse>> listOutgoing(
            @AuthenticationPrincipal String userId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        Pageable pageable = PageRequest.of(page, size);
        return ResponseEntity.ok(shareRequestService.listOutgoing(userId, pageable));
    }

    @PostMapping("/{id}/approve")
    public ResponseEntity<ShareRequestResponse> approve(
            @AuthenticationPrincipal String userId,
            @PathVariable String id) {
        return ResponseEntity.ok(shareRequestService.approve(userId, id));
    }

    @PostMapping("/{id}/reject")
    public ResponseEntity<ShareRequestResponse> reject(
            @AuthenticationPrincipal String userId,
            @PathVariable String id) {
        return ResponseEntity.ok(shareRequestService.reject(userId, id));
    }
}