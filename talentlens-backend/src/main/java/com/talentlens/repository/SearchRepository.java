package com.talentlens.repository;

import com.talentlens.model.Search;
import org.springframework.data.mongodb.repository.MongoRepository;

public interface SearchRepository extends MongoRepository<Search, String>, SearchRepositoryCustom {
    void deleteByUserId(String userId);
}
