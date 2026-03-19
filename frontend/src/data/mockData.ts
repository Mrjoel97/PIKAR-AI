export interface Testimonial {
    id: number;
    name: string;
    role: string;
    initials: string;
    color: string;
    quote: string;
}

export const TESTIMONIALS: Testimonial[] = [
    {
        id: 1,
        name: "Sarah Jenkins",
        role: "CTO at TechFlow",
        initials: "SJ",
        color: "#6366f1",
        quote: "Pikar AI revolutionized our workflow overnight. The automated insights are incredibly accurate and saved us 20 hours a week."
    },
    {
        id: 2,
        name: "David Chen",
        role: "Product Lead",
        initials: "DC",
        color: "#0891b2",
        quote: "The precision is unmatched in the industry. I've tried other tools, but Pikar stands out for its intuitive design."
    },
    {
        id: 3,
        name: "Elena Rodriguez",
        role: "Director of Ops",
        initials: "ER",
        color: "#7c3aed",
        quote: "Simply the best investment we made this year. It handles complex data processing like a charm."
    },
    {
        id: 4,
        name: "Michael Chang",
        role: "Senior Developer",
        initials: "MC",
        color: "#059669",
        quote: "Incredible speed and accuracy for our needs. The API documentation is thorough and the support team is responsive."
    },
    {
        id: 5,
        name: "Lisa Ray",
        role: "UX Designer",
        initials: "LR",
        color: "#d946ef",
        quote: "A game changer for our design team. The asset generation features allow us to prototype 10x faster."
    },
    {
        id: 6,
        name: "James Wilson",
        role: "Founder at StartupX",
        initials: "JW",
        color: "#ea580c",
        quote: "Highly recommended for enterprise use. Security compliance was our main concern and Pikar nailed it."
    }
];
