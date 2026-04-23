package com.talentlens.service.impl;

import com.talentlens.dto.request.CreateShareRequestRequest;
import com.talentlens.dto.response.PageResponse;
import com.talentlens.dto.response.RecruiterResponse;
import com.talentlens.dto.response.ShareRequestResponse;
import com.talentlens.mapper.ShareRequestMapper;
import com.talentlens.mapper.UserMapper;
import com.talentlens.model.Role;
import com.talentlens.model.Search;
import com.talentlens.model.ShareRequest;
import com.talentlens.model.ShareRequestStatus;
import com.talentlens.model.User;
import com.talentlens.repository.SearchRepository;
import com.talentlens.repository.ShareRequestRepository;
import com.talentlens.repository.UserRepository;
import com.talentlens.service.ShareRequestPolicy;
import com.talentlens.service.ShareRequestService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;

import java.time.Instant;

@Service
@RequiredArgsConstructor
public class ShareRequestServiceImpl implements ShareRequestService {

    private final UserRepository userRepository;
    private final SearchRepository searchRepository;
    private final ShareRequestRepository shareRequestRepository;
    private final ShareRequestMapper shareRequestMapper;
    private final UserMapper userMapper;
    private final ShareRequestPolicy shareRequestPolicy;

    @Override
    public PageResponse<RecruiterResponse> listRecruiters(Pageable pageable) {
        Page<User> page = userRepository.findByRole(Role.RECRUITER, pageable);
        return PageResponse.from(page.map(userMapper::toRecruiterResponse));
    }

    @Override
    public ShareRequestResponse createRequest(String requesterUserId, CreateShareRequestRequest request) {
        ShareRequestPolicy.CreateShareRequestContext context = shareRequestPolicy.validateCreateRequest(requesterUserId, request);

        ShareRequest entity = ShareRequest.builder()
                .searchId(context.searchId())
                .requesterUserId(context.requesterUserId())
                .ownerUserId(context.recruiterUserId())
                .status(ShareRequestStatus.PENDING)
                .requestedAt(Instant.now())
                .note(request.getNote())
                .build();

        ShareRequest saved = shareRequestRepository.save(entity);
        return shareRequestMapper.toResponse(saved);
    }

    @Override
    public PageResponse<ShareRequestResponse> listIncoming(String recruiterUserId, Pageable pageable) {
        Page<ShareRequest> page = shareRequestRepository.findByOwnerUserIdAndStatusOrderByRequestedAtDesc(
                recruiterUserId,
                ShareRequestStatus.PENDING,
                pageable
        );
        return PageResponse.from(page.map(shareRequestMapper::toResponse));
    }

    @Override
    public PageResponse<ShareRequestResponse> listOutgoing(String requesterUserId, Pageable pageable) {
        Page<ShareRequest> page = shareRequestRepository.findByRequesterUserIdOrderByRequestedAtDesc(requesterUserId, pageable);
        return PageResponse.from(page.map(shareRequestMapper::toResponse));
    }

    @Override
    public ShareRequestResponse approve(String recruiterUserId, String requestId) {
        ShareRequest request = shareRequestPolicy.loadPendingRequestForOwner(requestId, recruiterUserId);
        Search search = shareRequestPolicy.loadSearchOrThrow(request.getSearchId());
        searchRepository.addSharedUserAtomically(search.getId(), request.getRequesterUserId());

        request.setStatus(ShareRequestStatus.APPROVED);
        request.setResolvedAt(Instant.now());
        request.setResolvedBy(recruiterUserId);
        ShareRequest saved = shareRequestRepository.save(request);

        return shareRequestMapper.toResponse(saved);
    }

    @Override
    public ShareRequestResponse reject(String recruiterUserId, String requestId) {
        ShareRequest request = shareRequestPolicy.loadPendingRequestForOwner(requestId, recruiterUserId);

        request.setStatus(ShareRequestStatus.REJECTED);
        request.setResolvedAt(Instant.now());
        request.setResolvedBy(recruiterUserId);

        ShareRequest saved = shareRequestRepository.save(request);
        return shareRequestMapper.toResponse(saved);
    }
}