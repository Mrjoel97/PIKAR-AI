"use client";

import React, { useRef, useEffect, useState } from "react";

interface FadeInProps {
    children: React.ReactNode;
    delay?: number;
    className?: string;
    direction?: "up" | "down" | "left" | "right";
}

/**
 * Lightweight FadeIn using IntersectionObserver + CSS transitions.
 * Eliminates framer-motion from the landing page critical path,
 * reducing JS bundle size by ~40KB gzipped.
 */
const FadeIn: React.FC<FadeInProps> = ({
    children,
    delay = 0,
    className = "",
    direction = "up"
}) => {
    const ref = useRef<HTMLDivElement>(null);
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
        const el = ref.current;
        if (!el) return;

        const observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting) {
                    setIsVisible(true);
                    observer.unobserve(el);
                }
            },
            { rootMargin: '-80px', threshold: 0.01 }
        );

        observer.observe(el);
        return () => observer.disconnect();
    }, []);

    const getInitialTransform = () => {
        switch (direction) {
            case "left": return "translateX(-40px)";
            case "right": return "translateX(40px)";
            case "down": return "translateY(-40px)";
            case "up":
            default: return "translateY(40px)";
        }
    };

    return (
        <div
            ref={ref}
            className={className}
            style={{
                opacity: isVisible ? 1 : 0,
                transform: isVisible ? "translate(0)" : getInitialTransform(),
                transition: `opacity 0.6s cubic-bezier(0.21,0.47,0.32,0.98) ${delay}s, transform 0.6s cubic-bezier(0.21,0.47,0.32,0.98) ${delay}s`,
                willChange: isVisible ? 'auto' : 'opacity, transform',
            }}
        >
            {children}
        </div>
    );
};

export default FadeIn;
