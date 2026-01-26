/**
 * ID Registration System - Premium Landing Page
 * Flow of Identity Animations & Interactions
 */

(function () {
  'use strict';

  // ==========================================
  // INITIALIZATION
  // ==========================================

  document.addEventListener('DOMContentLoaded', () => {
    initCursorGlow();
    initNavbarScroll();
    initScrollAnimations();
    initScrollReveal();
    initRoleCardEffects();
    initMagneticButtons();
    initParallaxEffects();
    initTypingEffects();
    initSmoothScroll();
  });

  // ==========================================
  // CUSTOM CURSOR GLOW
  // ==========================================

  function initCursorGlow() {
    const cursor = document.getElementById('cursorGlow');
    if (!cursor) return;

    let mouseX = 0;
    let mouseY = 0;
    let cursorX = 0;
    let cursorY = 0;

    // Track mouse position
    document.addEventListener('mousemove', (e) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
    });

    // Smooth follow animation
    function animateCursor() {
      const dx = mouseX - cursorX;
      const dy = mouseY - cursorY;

      cursorX += dx * 0.08;
      cursorY += dy * 0.08;

      cursor.style.left = cursorX + 'px';
      cursor.style.top = cursorY + 'px';

      requestAnimationFrame(animateCursor);
    }

    animateCursor();
  }

  // ==========================================
  // NAVBAR SCROLL EFFECT
  // ==========================================

  function initNavbarScroll() {
    const navbar = document.getElementById('navBar');
    if (!navbar) return;

    function updateNavbar() {
      if (window.pageYOffset > 50) {
        navbar.classList.add('scrolled');
      } else {
        navbar.classList.remove('scrolled');
      }
    }

    window.addEventListener('scroll', updateNavbar, { passive: true });
    updateNavbar();
  }

  // ==========================================
  // SMOOTH SCROLL
  // ==========================================

  function initSmoothScroll() {
    const scrollLinks = document.querySelectorAll('a[href^="#"]');

    scrollLinks.forEach(link => {
      link.addEventListener('click', (e) => {
        const href = link.getAttribute('href');
        if (href === '#') return;

        const target = document.querySelector(href);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
          });
        }
      });
    });
  }

  // ==========================================
  // SCROLL-TRIGGERED ANIMATIONS
  // ==========================================

  function initScrollAnimations() {
    // Observe sections for in-view animations
    const sections = document.querySelectorAll(
      '.flow-section, .roles-section, .confidence-section'
    );

    const sectionObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('in-view');
        }
      });
    }, {
      threshold: 0.2,
      rootMargin: '-50px'
    });

    sections.forEach(section => sectionObserver.observe(section));



    // Animate flow paths when visible
    const flowSection = document.getElementById('flowSection');
    if (flowSection) {
      const flowObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('in-view');
          }
        });
      }, { threshold: 0.3 });

      flowObserver.observe(flowSection);
    }
  }

  // ==========================================
  // SCROLL REVEAL - Lightweight GSAP-inspired
  // ==========================================

  function initScrollReveal() {
    const revealElements = document.querySelectorAll('.scroll-reveal');
    
    if (!revealElements.length) return;

    // Check for reduced motion preference
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    
    if (prefersReducedMotion) {
      // If reduced motion is preferred, reveal all elements immediately
      revealElements.forEach(el => el.classList.add('revealed'));
      return;
    }

    const revealObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          // Add revealed class to trigger the animation
          entry.target.classList.add('revealed');
          // Unobserve after revealing - animations trigger once only
          revealObserver.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.15,
      rootMargin: '-20px 0px -20px 0px'
    });

    revealElements.forEach(el => revealObserver.observe(el));
  }

  // ==========================================
  // ROLE CARD INTERACTIVE EFFECTS
  // ==========================================

  function initRoleCardEffects() {
    const roleCards = document.querySelectorAll('.role-card');

    roleCards.forEach(card => {
      // 3D tilt effect on mouse move
      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const centerX = rect.width / 2;
        const centerY = rect.height / 2;

        const rotateX = (y - centerY) / 25;
        const rotateY = (centerX - x) / 25;

        card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-8px)`;
      });

      card.addEventListener('mouseleave', () => {
        card.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) translateY(0)';
      });

      // Animate preview elements on hover
      const stepItems = card.querySelectorAll('.step-item:not(.step-active)');

      card.addEventListener('mouseenter', () => {
        stepItems.forEach((item, index) => {
          setTimeout(() => {
            const dot = item.querySelector('.step-dot');
            if (dot) {
              dot.style.background = 'var(--color-green)';
              dot.style.boxShadow = '0 0 10px var(--color-green-glow)';
            }
          }, 300 + (index * 200));
        });
      });

      card.addEventListener('mouseleave', () => {
        stepItems.forEach(item => {
          const dot = item.querySelector('.step-dot');
          if (dot) {
            dot.style.background = '';
            dot.style.boxShadow = '';
          }
        });
      });
    });
  }

  // ==========================================
  // MAGNETIC BUTTON EFFECT
  // ==========================================

  function initMagneticButtons() {
    const magneticElements = document.querySelectorAll('.role-cta, .confidence-cta, .hero-cta, .nav-link-accent');

    magneticElements.forEach(btn => {
      btn.addEventListener('mousemove', (e) => {
        const rect = btn.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;

        btn.style.transform = `translate(${x * 0.2}px, ${y * 0.2}px)`;
      });

      btn.addEventListener('mouseleave', () => {
        btn.style.transform = '';
      });
    });
  }

  // ==========================================
  // PARALLAX EFFECTS
  // ==========================================

  function initParallaxEffects() {
    const idCard = document.getElementById('idCard');
    const particles = document.querySelectorAll('.particle');

    if (!idCard) return;

    let ticking = false;

    window.addEventListener('scroll', () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          updateParallax();
          ticking = false;
        });
        ticking = true;
      }
    }, { passive: true });

    function updateParallax() {
      const scrolled = window.pageYOffset;
      const heroSection = document.getElementById('hero');

      if (!heroSection) return;

      const heroRect = heroSection.getBoundingClientRect();

      if (heroRect.bottom > 0) {
        // Parallax for ID card
        const cardOffset = scrolled * 0.12;
        const existingTransform = idCard.style.transform || '';

        // Only update translateY, preserve other transforms from animation
        if (!existingTransform.includes('translateY')) {
          idCard.style.setProperty('--parallax-y', `${-cardOffset}px`);
        }

        // Parallax for particles
        particles.forEach((particle, index) => {
          const speed = 0.08 + (index * 0.04);
          particle.style.transform = `translateY(${-scrolled * speed}px)`;
        });
      }
    }
  }

  // ==========================================
  // TYPING EFFECT
  // ==========================================

  function initTypingEffects() {
    const typingElements = document.querySelectorAll('.typing-effect');

    typingElements.forEach(el => {
      const text = el.textContent;
      el.textContent = '';
      el.style.minWidth = '120px';

      let charIndex = 0;
      const typingSpeed = 70;

      // Delay before typing starts
      setTimeout(() => {
        function type() {
          if (charIndex < text.length) {
            el.textContent += text.charAt(charIndex);
            charIndex++;
            setTimeout(type, typingSpeed);
          }
        }
        type();
      }, 1500);
    });
  }

  // ==========================================
  // ANIMATE ID CARD INFO ROWS
  // ==========================================

  const idCardContainer = document.getElementById('idCardContainer');
  if (idCardContainer) {
    const cardObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const infoRows = entry.target.querySelectorAll('.info-row');
          infoRows.forEach((row, index) => {
            row.style.animationDelay = `${0.8 + (index * 0.2)}s`;
            row.classList.add('animate-in');
          });
        }
      });
    }, { threshold: 0.5 });

    cardObserver.observe(idCardContainer);
  }

  // ==========================================
  // PERFORMANCE OPTIMIZATION
  // ==========================================

  // Reduce animations when tab is not visible
  document.addEventListener('visibilitychange', () => {
    const root = document.documentElement;
    if (document.hidden) {
      root.style.setProperty('--animation-state', 'paused');
    } else {
      root.style.setProperty('--animation-state', 'running');
    }
  });

  // Detect reduced motion preference
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.documentElement.style.setProperty('--ease-smooth', 'linear');
    document.documentElement.style.setProperty('--duration-fast', '0ms');
    document.documentElement.style.setProperty('--duration-normal', '0ms');
    document.documentElement.style.setProperty('--duration-slow', '0ms');
  }

  // Preload fonts
  if ('fonts' in document) {
    Promise.all([
      document.fonts.load('400 1em Inter'),
      document.fonts.load('600 1em Inter'),
      document.fonts.load('700 1em Inter'),
    ]).then(() => {
      document.body.classList.add('fonts-loaded');
    });
  }

})();
