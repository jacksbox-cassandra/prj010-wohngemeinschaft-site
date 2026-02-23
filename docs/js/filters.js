/**
 * Filters.js - Client-side filtering and sorting for property listings
 * No dependencies, pure vanilla JavaScript
 */

class PropertyFilters {
    constructor() {
        this.candidates = [];
        this.filteredCandidates = [];
        this.currentFilter = 'all';
        this.currentSort = 'score';
        this.currentSearch = '';
        
        this.init();
    }
    
    init() {
        // Get all candidate elements
        this.loadCandidates();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Load state from URL
        this.loadStateFromURL();
        
        // Make filter bar sticky
        this.setupStickyFilter();
        
        // Initial render
        this.applyFilters();
    }
    
    loadCandidates() {
        const grid = document.getElementById('candidatesGrid');
        if (!grid) return;
        
        this.candidates = Array.from(grid.children).map(card => ({
            element: card,
            type: card.dataset.type || 'buy',
            score: parseInt(card.dataset.score || '0'),
            price: parseInt(card.dataset.price || '0'),
            size: parseInt(card.dataset.size || '0'),
            id: card.dataset.id || '',
            status: card.dataset.status || 'active',
            title: card.querySelector('.candidate-title')?.textContent || '',
            location: card.querySelector('.candidate-location')?.textContent || ''
        }));
        
        this.filteredCandidates = [...this.candidates];
    }
    
    setupEventListeners() {
        // Filter buttons
        const filterBtns = document.querySelectorAll('.filter-btn');
        filterBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const filter = e.target.dataset.filter;
                this.setFilter(filter);
            });
        });
        
        // Sort select
        const sortSelect = document.getElementById('sortSelect');
        if (sortSelect) {
            sortSelect.addEventListener('change', (e) => {
                this.setSort(e.target.value);
            });
        }
        
        // Search input
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.setSearch(e.target.value);
            });
        }
        
        // Clear search button
        const clearBtn = document.getElementById('clearSearch');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearSearch();
            });
        }
    }
    
    setupStickyFilter() {
        const filterBar = document.getElementById('filterBar');
        if (!filterBar) return;
        
        const container = document.querySelector('.container');
        const filterOffset = filterBar.offsetTop;
        
        window.addEventListener('scroll', () => {
            if (window.pageYOffset >= filterOffset) {
                filterBar.classList.add('sticky');
                if (container) {
                    container.style.paddingTop = filterBar.offsetHeight + 'px';
                }
            } else {
                filterBar.classList.remove('sticky');
                if (container) {
                    container.style.paddingTop = '2rem';
                }
            }
        });
    }
    
    setFilter(filter) {
        this.currentFilter = filter;
        this.updateFilterButtons();
        this.applyFilters();
        this.updateURL();
    }
    
    setSort(sort) {
        this.currentSort = sort;
        this.applyFilters();
        this.updateURL();
    }
    
    setSearch(search) {
        this.currentSearch = search.toLowerCase().trim();
        this.applyFilters();
        this.updateURL();
        
        // Show/hide clear button
        const clearBtn = document.getElementById('clearSearch');
        if (clearBtn) {
            clearBtn.style.display = this.currentSearch ? 'block' : 'none';
        }
    }
    
    clearSearch() {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.value = '';
        }
        this.setSearch('');
    }
    
    updateFilterButtons() {
        const filterBtns = document.querySelectorAll('.filter-btn');
        filterBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.filter === this.currentFilter);
        });
    }
    
    applyFilters() {
        // Start with all candidates
        let filtered = [...this.candidates];
        
        // Apply type filter
        if (this.currentFilter !== 'all') {
            filtered = filtered.filter(c => c.type === this.currentFilter);
        }
        
        // Apply search filter
        if (this.currentSearch) {
            filtered = filtered.filter(c => 
                c.title.toLowerCase().includes(this.currentSearch) ||
                c.location.toLowerCase().includes(this.currentSearch) ||
                c.id.toLowerCase().includes(this.currentSearch)
            );
        }
        
        // Apply sorting
        filtered.sort((a, b) => {
            switch (this.currentSort) {
                case 'score':
                    return b.score - a.score; // High to low
                case 'price-asc':
                    return a.price - b.price; // Low to high
                case 'price-desc':
                    return b.price - a.price; // High to low
                case 'size':
                    return b.size - a.size; // Large to small
                case 'id':
                    return a.id.localeCompare(b.id); // A to Z
                default:
                    return 0;
            }
        });
        
        this.filteredCandidates = filtered;
        this.renderResults();
    }
    
    renderResults() {
        const grid = document.getElementById('candidatesGrid');
        const noResults = document.getElementById('noResults');
        
        if (!grid) return;
        
        // Hide all candidates first
        this.candidates.forEach(c => {
            c.element.style.display = 'none';
        });
        
        if (this.filteredCandidates.length === 0) {
            // Show no results message
            if (noResults) {
                noResults.style.display = 'block';
            }
        } else {
            // Hide no results message
            if (noResults) {
                noResults.style.display = 'none';
            }
            
            // Show and reorder filtered candidates
            this.filteredCandidates.forEach((candidate, index) => {
                candidate.element.style.display = 'block';
                candidate.element.style.order = index;
            });
        }
        
        // Update filter button counts
        this.updateFilterCounts();
    }
    
    updateFilterCounts() {
        const allCount = this.candidates.length;
        const buyCount = this.candidates.filter(c => c.type === 'buy').length;
        const rentCount = this.candidates.filter(c => c.type === 'rent').length;
        
        const filterBtns = document.querySelectorAll('.filter-btn');
        filterBtns.forEach(btn => {
            const filter = btn.dataset.filter;
            let count = allCount;
            
            if (filter === 'buy') count = buyCount;
            else if (filter === 'rent') count = rentCount;
            
            // Update button text
            const baseText = btn.textContent.split('(')[0].trim();
            btn.textContent = `${baseText} (${count})`;
        });
    }
    
    loadStateFromURL() {
        const params = new URLSearchParams(window.location.search);
        
        // Load filter
        const type = params.get('type');
        if (type && ['all', 'buy', 'rent'].includes(type)) {
            this.currentFilter = type;
        }
        
        // Load sort
        const sort = params.get('sort');
        if (sort) {
            this.currentSort = sort;
            const sortSelect = document.getElementById('sortSelect');
            if (sortSelect) {
                sortSelect.value = sort;
            }
        }
        
        // Load search
        const search = params.get('search');
        if (search) {
            this.currentSearch = search.toLowerCase();
            const searchInput = document.getElementById('searchInput');
            if (searchInput) {
                searchInput.value = search;
            }
        }
        
        this.updateFilterButtons();
    }
    
    updateURL() {
        const params = new URLSearchParams();
        
        if (this.currentFilter !== 'all') {
            params.set('type', this.currentFilter);
        }
        
        if (this.currentSort !== 'score') {
            params.set('sort', this.currentSort);
        }
        
        if (this.currentSearch) {
            params.set('search', this.currentSearch);
        }
        
        const newURL = params.toString() ? 
            `${window.location.pathname}?${params.toString()}` : 
            window.location.pathname;
            
        // Update URL without page reload
        window.history.replaceState({}, '', newURL);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.propertyFilters = new PropertyFilters();
});

// Graceful degradation - ensure basic functionality works without JS
if (!document.getElementById('candidatesGrid')) {
    console.warn('PropertyFilters: candidatesGrid not found - filters disabled');
}