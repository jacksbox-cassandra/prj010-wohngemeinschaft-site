/**
 * Gallery.js - Image lightbox with navigation
 * Mobile-friendly with optional swipe support
 */

class ImageGallery {
    constructor() {
        this.isOpen = false;
        this.currentImages = [];
        this.currentIndex = 0;
        this.currentId = '';
        
        this.init();
    }
    
    init() {
        this.createLightboxHTML();
        this.setupEventListeners();
        this.setupKeyboardNavigation();
    }
    
    createLightboxHTML() {
        // Create lightbox overlay
        const lightbox = document.createElement('div');
        lightbox.id = 'lightbox';
        lightbox.className = 'lightbox';
        lightbox.innerHTML = `
            <div class="lightbox-overlay" onclick="gallery.close()"></div>
            <div class="lightbox-container">
                <button class="lightbox-close" onclick="gallery.close()">✕</button>
                <button class="lightbox-nav lightbox-prev" onclick="gallery.prev()">‹</button>
                <button class="lightbox-nav lightbox-next" onclick="gallery.next()">›</button>
                <div class="lightbox-content">
                    <img id="lightboxImage" src="" alt="">
                    <div class="lightbox-info">
                        <span class="lightbox-counter"></span>
                        <span class="lightbox-title"></span>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(lightbox);
    }
    
    setupEventListeners() {
        // Touch/swipe support for mobile
        let startX = 0;
        let startY = 0;
        
        const lightbox = document.getElementById('lightbox');
        if (!lightbox) return;
        
        // Touch start
        lightbox.addEventListener('touchstart', (e) => {
            if (!this.isOpen) return;
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        }, { passive: true });
        
        // Touch move (prevent scrolling)
        lightbox.addEventListener('touchmove', (e) => {
            if (!this.isOpen) return;
            e.preventDefault();
        }, { passive: false });
        
        // Touch end (detect swipe)
        lightbox.addEventListener('touchend', (e) => {
            if (!this.isOpen) return;
            
            const endX = e.changedTouches[0].clientX;
            const endY = e.changedTouches[0].clientY;
            const deltaX = endX - startX;
            const deltaY = endY - startY;
            
            // Check if it's a horizontal swipe (not vertical scroll)
            if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 50) {
                if (deltaX > 0) {
                    this.prev(); // Swipe right = previous
                } else {
                    this.next(); // Swipe left = next
                }
            }
        }, { passive: true });
    }
    
    setupKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            if (!this.isOpen) return;
            
            switch (e.key) {
                case 'Escape':
                    this.close();
                    break;
                case 'ArrowLeft':
                    this.prev();
                    break;
                case 'ArrowRight':
                    this.next();
                    break;
            }
        });
    }
    
    open(candidateId) {
        // Get images for this candidate
        const images = window.galleries && window.galleries[candidateId];
        if (!images || !images.length) {
            console.warn('No gallery images found for:', candidateId);
            return;
        }
        
        this.currentImages = images;
        this.currentIndex = 0;
        this.currentId = candidateId;
        this.isOpen = true;
        
        // Show lightbox
        const lightbox = document.getElementById('lightbox');
        if (lightbox) {
            lightbox.classList.add('active');
            document.body.classList.add('lightbox-open');
        }
        
        this.updateImage();
        this.updateNavigation();
    }
    
    close() {
        this.isOpen = false;
        
        const lightbox = document.getElementById('lightbox');
        if (lightbox) {
            lightbox.classList.remove('active');
            document.body.classList.remove('lightbox-open');
        }
        
        this.currentImages = [];
        this.currentIndex = 0;
        this.currentId = '';
    }
    
    next() {
        if (this.currentImages.length <= 1) return;
        
        this.currentIndex = (this.currentIndex + 1) % this.currentImages.length;
        this.updateImage();
        this.updateNavigation();
    }
    
    prev() {
        if (this.currentImages.length <= 1) return;
        
        this.currentIndex = (this.currentIndex - 1 + this.currentImages.length) % this.currentImages.length;
        this.updateImage();
        this.updateNavigation();
    }
    
    updateImage() {
        const img = document.getElementById('lightboxImage');
        const counter = document.querySelector('.lightbox-counter');
        const title = document.querySelector('.lightbox-title');
        
        if (!img) return;
        
        const currentImg = this.currentImages[this.currentIndex];
        img.src = currentImg;
        img.alt = `${this.currentId} - Bild ${this.currentIndex + 1}`;
        
        // Update counter
        if (counter) {
            counter.textContent = `${this.currentIndex + 1} / ${this.currentImages.length}`;
        }
        
        // Update title
        if (title) {
            title.textContent = this.currentId;
        }
    }
    
    updateNavigation() {
        const prevBtn = document.querySelector('.lightbox-prev');
        const nextBtn = document.querySelector('.lightbox-next');
        
        const hasMultiple = this.currentImages.length > 1;
        
        if (prevBtn) {
            prevBtn.style.display = hasMultiple ? 'block' : 'none';
        }
        
        if (nextBtn) {
            nextBtn.style.display = hasMultiple ? 'block' : 'none';
        }
    }
}

// Global function to open gallery (called from HTML)
function openGallery(candidateId) {
    if (window.gallery) {
        window.gallery.open(candidateId);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.gallery = new ImageGallery();
});

// Graceful degradation - fallback for no JS
if (!document.querySelector('.candidate-image.has-gallery')) {
    console.info('ImageGallery: No galleries found - lightbox disabled');
}