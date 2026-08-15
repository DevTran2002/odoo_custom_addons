/** @odoo-module **/
/**
 * TH Base Performance - In-Memory ORM Cache Service
 * Sử dụng bộ nhớ RAM (In-Memory Map) thay vì sessionStorage để tránh lỗi QuotaExceededError (đầy 5MB storage của trình duyệt).
 * TTL: 30 giây.
 */

import { ORM } from "@web/core/orm_service";
import { patch } from "@web/core/utils/patch";

const TH_CACHE_TTL_MS = 30_000; // 30 giây

function buildCacheKey(model, method, kwargs) {
    try {
        return `th_perf:${model}:${method}:${JSON.stringify(kwargs)}`;
    } catch (e) {
        return null;
    }
}

/**
 * Bộ nhớ Cache RAM tạm thời (In-Memory Map)
 * Tránh hoàn toàn giới hạn 5MB của sessionStorage
 */
const RAM_CACHE = new Map();

const ThOrmCache = {
    get(key) {
        if (!key || !RAM_CACHE.has(key)) return null;
        const entry = RAM_CACHE.get(key);
        if (Date.now() - entry.ts > TH_CACHE_TTL_MS) {
            RAM_CACHE.delete(key);
            return null;
        }
        return entry.data;
    },

    set(key, data) {
        if (!key) return;
        RAM_CACHE.set(key, { data, ts: Date.now() });

        // Tự động dọn dẹp các cache quá 500 mục để tiết kiệm RAM
        if (RAM_CACHE.size > 500) {
            const now = Date.now();
            for (const [k, val] of RAM_CACHE.entries()) {
                if (now - val.ts > TH_CACHE_TTL_MS) {
                    RAM_CACHE.delete(k);
                }
            }
        }
    },

    invalidateModel(model) {
        const prefix = `th_perf:${model}:`;
        for (const key of RAM_CACHE.keys()) {
            if (key.startsWith(prefix)) {
                RAM_CACHE.delete(key);
            }
        }
    },
};

patch(ORM.prototype, "th_base_performance.orm_cache", {
    webSearchRead(model, domain, fields, kwargs = {}) {
        const cacheKey = buildCacheKey(model, "web_search_read", {
            domain,
            fields,
            ...kwargs,
        });

        const cached = ThOrmCache.get(cacheKey);
        if (cached !== null) {
            return Promise.resolve(cached);
        }

        return this._super(model, domain, fields, kwargs).then((result) => {
            ThOrmCache.set(cacheKey, result);
            return result;
        });
    },

    call(model, method, args = [], kwargs = {}) {
        const CACHEABLE_METHODS = [
            "search_panel_select_range",
            "search_panel_select_multi_range",
        ];

        const WRITE_METHODS = ["create", "write", "unlink", "copy"];

        if (WRITE_METHODS.includes(method)) {
            ThOrmCache.invalidateModel(model);
            return this._super(model, method, args, kwargs);
        }

        if (CACHEABLE_METHODS.includes(method)) {
            const cacheKey = buildCacheKey(model, method, { args, ...kwargs });
            const cached = ThOrmCache.get(cacheKey);
            if (cached !== null) {
                return Promise.resolve(cached);
            }

            return this._super(model, method, args, kwargs).then((result) => {
                ThOrmCache.set(cacheKey, result);
                return result;
            });
        }

        return this._super(model, method, args, kwargs);
    },
});

export { ThOrmCache };
