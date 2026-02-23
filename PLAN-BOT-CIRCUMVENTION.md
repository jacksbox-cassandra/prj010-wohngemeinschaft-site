# Bot Protection Circumvention Plan
## PRJ010 Wohngemeinschaft Property Search

### Current Status
- **Kleinanzeigen**: Working with basic HTTP requests
- **Immowelt**: Blocked (410 Gone errors) - bot detection active
- **ImmobilienScout24**: Need to test current blocking status

### Strategy Recommendations

## Strategy A: Browser Automation (RECOMMENDED)
**Use OpenClaw browser tool with real browser automation**

### Implementation Details
- **Tool**: OpenClaw browser tool with `profile="openclaw"`
- **Technology**: Playwright/CDP through OpenClaw's browser control
- **Benefits**: Real browser fingerprint, cookies, localStorage, human-like behavior
- **Implementation effort**: ~8-12 hours
- **Cost**: $0 (included in OpenClaw)

### Implementation Steps
1. **Modify source handlers** to use `browser` tool instead of requests
2. **Add human-like delays** (2-5 seconds between requests)
3. **Implement cookie/session management** across scraping runs
4. **Add random mouse movements** and scrolling to mimic humans
5. **Handle JavaScript-heavy sites** that require rendering

### Sample Implementation
```python
# In source handlers
browser_result = browser(
    action="open",
    profile="openclaw", 
    targetUrl=search_url
)

# Wait for content to load
browser(action="act", request={"kind": "wait", "timeMs": 3000})

# Extract listings with JavaScript execution
content = browser(action="evaluate", javaScript="document.body.innerHTML")
```

### Advantages
- ✅ Bypasses most bot detection
- ✅ Handles JavaScript rendering
- ✅ Real browser fingerprint
- ✅ Can solve CAPTCHAs manually if needed
- ✅ No additional costs

### Disadvantages
- ⚠️ Slower than HTTP requests (3-5x)
- ⚠️ More complex implementation
- ⚠️ Requires more system resources

---

## Strategy B: Residential Proxies
**Rotate IP addresses to avoid detection**

### Service Providers
- **Brightdata** (formerly Luminati): Premium service, $50-100/month
- **Oxylabs**: Enterprise-grade, $75-150/month  
- **Smartproxy**: Budget option, $25-50/month

### Implementation Details
- **Rotation frequency**: Every 10-20 requests
- **Geographic targeting**: German residential IPs
- **Implementation effort**: ~4-6 hours
- **Cost**: $50-100/month

### Implementation Steps
1. **Sign up** for residential proxy service
2. **Integrate proxy rotation** into BaseScraper class
3. **Add IP rotation logic** with request counting
4. **Implement retry logic** for failed requests
5. **Monitor success rates** and adjust rotation frequency

### Advantages
- ✅ Maintains fast HTTP requests
- ✅ Simple integration
- ✅ Works with existing code structure
- ✅ Minimal system resource impact

### Disadvantages
- ❌ Ongoing monthly costs
- ⚠️ May still trigger detection on some sites
- ⚠️ Quality varies by provider
- ⚠️ Potential IP blocks from proxy farms

---

## Strategy C: Session Management
**Maintain authenticated sessions and respect rate limits**

### Implementation Details
- **Session persistence**: Save cookies between runs
- **Rate limiting**: 1 request every 2-3 seconds
- **Request patterns**: Mimic human browsing behavior
- **Implementation effort**: ~3-4 hours
- **Cost**: $0

### Implementation Steps
1. **Add session storage** to BaseScraper (pickle/JSON cookies)
2. **Implement rate limiting** with random delays (2-5 seconds)
3. **Add request headers** that mimic real browsers
4. **Handle session expiry** and re-authentication
5. **Rotate User-Agents** from real browser pool

### Session Storage Example
```python
class BaseScraper:
    def __init__(self):
        self.session_file = f"sessions/{self.source_name}_session.json"
        self.load_session()
    
    def save_session(self):
        cookies = self.session.cookies.get_dict()
        with open(self.session_file, 'w') as f:
            json.dump(cookies, f)
```

### Advantages
- ✅ No additional costs
- ✅ Simple implementation
- ✅ Works with existing infrastructure
- ✅ Respects site policies

### Disadvantages
- ⚠️ May not work against sophisticated detection
- ⚠️ Requires careful rate limiting
- ⚠️ Sessions may expire frequently

---

## Strategy D: API Access
**Use official APIs where available**

### Research Findings

#### ImmobilienScout24
- **Partner API**: Available for certified partners
- **Requirements**: Business verification, API agreement
- **Cost**: Varies by usage (typically €500+ setup)
- **Access process**: 2-4 weeks approval

#### Immowelt
- **Public API**: Not publicly available
- **Partner program**: Exists for real estate professionals
- **Alternative**: Data licensing agreements

#### Kleinanzeigen
- **No public API**: Only internal/partner access
- **eBay connection**: Might offer data access through eBay APIs

### Implementation Effort
- **Research and applications**: ~8-16 hours
- **Integration development**: ~20-40 hours per API
- **Cost**: €500-2000+ in setup fees

### Advantages
- ✅ Legitimate access
- ✅ Stable, supported endpoints
- ✅ No blocking concerns
- ✅ Better data quality

### Disadvantages
- ❌ High setup costs
- ❌ Business verification required
- ❌ Long approval processes
- ❌ Usage restrictions and fees

---

## Strategy E: Hybrid Approach (RECOMMENDED)
**Use different strategies per source based on blocking status**

### Source-Specific Strategies
1. **Kleinanzeigen**: Session Management (working, just needs rate limiting)
2. **Immowelt**: Browser Automation (heavily blocked)
3. **ImmobilienScout24**: Test current status → Browser Automation if blocked

### Implementation Plan
**Phase 1 (Week 1): Session Management for Kleinanzeigen**
- Add rate limiting and session persistence
- Improve request headers and user-agent rotation
- Test stability over multiple runs

**Phase 2 (Week 2): Browser Automation for Immowelt**
- Implement OpenClaw browser tool integration
- Add human-like delays and interactions
- Test bypassing 410 errors

**Phase 3 (Week 3): ImmobilienScout24 Assessment**
- Test current blocking status
- Implement browser automation if needed
- Optimize performance across all sources

### Effort Estimation
- **Total implementation**: ~16-20 hours
- **Testing and optimization**: ~8-12 hours
- **Total project time**: ~3-4 weeks

### Cost Analysis
- **Development time**: ~30 hours × €50/hour = €1,500
- **Operational costs**: €0/month (using OpenClaw browser)
- **Total first year**: €1,500

---

## Recommended Implementation Strategy

### Primary Choice: **Hybrid Approach (Strategy E)**

**Reasoning:**
1. **Cost-effective**: No ongoing proxy costs
2. **Flexible**: Different solutions per source
3. **Maintainable**: Uses OpenClaw tools already available
4. **Scalable**: Can add more sources with appropriate strategy

### Implementation Priority
1. ✅ **Immediate**: Fix URL validation and deduplication (completed)
2. 🔄 **Week 1**: Session management for Kleinanzeigen
3. 🔄 **Week 2**: Browser automation for Immowelt
4. 🔄 **Week 3**: Assess and implement ImmobilienScout24 solution

### Fallback Options
- If browser automation insufficient → **Strategy B** (Residential Proxies)
- For long-term stability → **Strategy D** (API Access)

### Success Metrics
- **Bypass rate**: >90% successful requests per source
- **Data quality**: >95% valid property listings
- **Performance**: <5 minutes total scraping time
- **Stability**: Works consistently over 30+ days

### Risk Assessment
**Low Risk**: Strategy C (Session Management) - already partially working
**Medium Risk**: Strategy A (Browser Automation) - depends on site complexity
**High Risk**: Strategy B (Proxies) - detection algorithms evolving
**Very High Risk**: Strategy D (APIs) - business requirements and costs

---

## Next Steps

1. **Test current status** of ImmobilienScout24 blocking
2. **Implement session management** for Kleinanzeigen 
3. **Begin browser automation** implementation for Immowelt
4. **Monitor success rates** and adjust strategies as needed
5. **Document performance** and create maintenance procedures

**Timeline**: 3-4 weeks for full implementation
**Budget**: €1,500 development time (no ongoing costs)
**Expected outcome**: Reliable scraping across all three sources