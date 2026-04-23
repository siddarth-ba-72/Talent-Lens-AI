package com.talentlens.repository;

import com.talentlens.model.ShareRequest;
import com.talentlens.model.ShareRequestStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.Optional;

public interface ShareRequestRepository extends MongoRepository<ShareRequest, String> {
    Page<ShareRequest> findByOwnerUserIdAndStatusOrderByRequestedAtDesc(
            String ownerUserId,
            ShareRequestStatus status,
            Pageable pageable
    );

    Page<ShareRequest> findByRequesterUserIdOrderByRequestedAtDesc(String requesterUserId, Pageable pageable);

    boolean existsBySearchIdAndRequesterUserIdAndStatus(
            String searchId,
            String requesterUserId,
            ShareRequestStatus status
    );

    Optional<ShareRequest> findByIdAndOwnerUserId(String id, String ownerUserId);
}