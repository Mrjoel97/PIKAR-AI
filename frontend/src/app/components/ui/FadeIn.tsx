"use client";

import { motion } from "framer-motion";
import React from "react";

interface FadeInProps {
    children: React.ReactNode;
    delay?: number;
    className?: string;
    direction?: "up" | "down" | "left" | "right";
}

const FadeIn: React.FC<FadeInProps> = ({
    children,
    delay = 0,
    className = "",
    direction = "up"
}) => {

    const getVariants = () => {
        const distance = 40;
        switch (direction) {
            case "left":
                return { hidden: { opacity: 0, x: -distance }, visible: { opacity: 1, x: 0 } };
            case "right":
                return { hidden: { opacity: 0, x: distance }, visible: { opacity: 1, x: 0 } };
            case "down":
                return { hidden: { opacity: 0, y: -distance }, visible: { opacity: 1, y: 0 } };
            case "up":
            default:
                return { hidden: { opacity: 0, y: distance }, visible: { opacity: 1, y: 0 } };
        }
    };

    return (
        <motion.div
            className={className}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            transition={{
                duration: 0.6,
                delay: delay,
                ease: [0.21, 0.47, 0.32, 0.98] // Smooth cubic-bezier
            }}
            variants={getVariants()}
        >
            {children}
        </motion.div>
    );
};

export default FadeIn;
