package com.talentlens.service;

import com.talentlens.dto.request.CreateShareRequestRequest;
import com.talentlens.exception.DuplicateResourceException;
import com.talentlens.exception.ForbiddenException;
import com.talentlens.exception.ResourceNotFoundException;
import com.talentlens.model.Role;
import com.talentlens.model.Search;
import com.talentlens.model.ShareRequest;
import com.talentlens.model.ShareRequestStatus;
import com.talentlens.model.User;
import com.talentlens.repository.SearchRepository;
import com.talentlens.repository.ShareRequestRepository;
import com.talentlens.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class ShareRequestPolicy {

    private final UserRepository userRepository;
    private final SearchRepository searchRepository;
    private final ShareRequestRepository shareRequestRepository;

    public CreateShareRequestContext validateCreateRequest(String requesterUserId, CreateShareRequestRequest request) {
        User requester = userRepository.findById(requesterUserId)
                .orElseThrow(() -> new ResourceNotFoundException("User not found"));
        if (requester.getRole() != Role.HIRING_MANAGER) {
            throw new ForbiddenException("Only hiring managers can request search access");
        }

        User recruiter = userRepository.findById(request.getRecruiterUserId())
                .orElseThrow(() -> new ResourceNotFoundException("Recruiter not found: " + request.getRecruiterUserId()));
        if (recruiter.getRole() != Role.RECRUITER) {
            throw new ForbiddenException("Target user is not a recruiter");
        }

        Search search = searchRepository.findById(request.getSearchId())
                .orElseThrow(() -> new ResourceNotFoundException("Search not found: " + request.getSearchId()));

        if (!search.getUserId().equals(request.getRecruiterUserId())) {
            throw new ResourceNotFoundException("Invalid search and recruiter combination");
        }

        if (requesterUserId.equals(search.getUserId())) {
            throw new ForbiddenException("Search owner cannot create a share request");
        }

        if (search.getSharedWith() != null && search.getSharedWith().contains(requesterUserId)) {
            throw new DuplicateResourceException("Search is already shared with this user");
        }

        boolean hasPending = shareRequestRepository.existsBySearchIdAndRequesterUserIdAndStatus(
                request.getSearchId(),
                requesterUserId,
                ShareRequestStatus.PENDING
        );
        if (hasPending) {
            throw new DuplicateResourceException("A pending share request already exists for this search");
        }

        return new CreateShareRequestContext(requesterUserId, request.getRecruiterUserId(), request.getSearchId());
    }

    public ShareRequest loadPendingRequestForOwner(String requestId, String recruiterUserId) {
        ShareRequest request = shareRequestRepository.findByIdAndOwnerUserId(requestId, recruiterUserId)
                .orElseThrow(() -> new ResourceNotFoundException("Share request not found: " + requestId));

        if (request.getStatus() != ShareRequestStatus.PENDING) {
            throw new DuplicateResourceException("Share request is already resolved");
        }
        return request;
    }

    public Search loadSearchOrThrow(String searchId) {
        return searchRepository.findById(searchId)
                .orElseThrow(() -> new ResourceNotFoundException("Search not found: " + searchId));
    }

    public record CreateShareRequestContext(
            String requesterUserId,
            String recruiterUserId,
            String searchId
    ) {}
}
