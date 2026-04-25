package com.talentlens.repository;

import com.talentlens.model.Search;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.mongodb.repository.MongoRepository;

public interface SearchRepository extends MongoRepository<Search, String>, SearchRepositoryCustom {
    void deleteByUserId(String userId);
    Page<Search> findByUserId(String userId, Pageable pageable);
}
