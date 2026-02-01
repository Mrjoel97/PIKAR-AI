export interface Testimonial {
    id: number;
    name: string;
    role: string;
    image: string;
    quote: string;
}

export const TESTIMONIALS: Testimonial[] = [
    {
        id: 1,
        name: "Sarah Jenkins",
        role: "CTO at TechFlow",
        image: "https://lh3.googleusercontent.com/aida-public/AB6AXuA9mF_JXUTZWBkcyCABN-_TQW1W2aFlkqDT6feYCmeRCR9xy0VBRyfC48qe6-eaYbU-H93-PWc_nN-jMiicUlgpddmgqGzFEpkWaNeDSbCqBAmKoKcqA3S6xXDyVP-wJ6s58wQHqGKGw9KoNxREEpLCFQVY7kAV8qiOjpCZZej0Or186wxRxbVWBAX_vYYYI212KeWIcBHkIPSl1u2XQfOaih5RHxkLba0QJOXIX8bZSR_5OoyUU4bwemKXov2u4GnPhBNJjJljxcI",
        quote: "Pikar AI revolutionized our workflow overnight. The automated insights are incredibly accurate and saved us 20 hours a week."
    },
    {
        id: 2,
        name: "David Chen",
        role: "Product Lead",
        image: "https://lh3.googleusercontent.com/aida-public/AB6AXuC2LaU2JXBwkZJa4qCcfF7ya16EIurTJJNUV1nJiiqhdy9GzIN6ofBtEmc16SB6J3rBKVQWnQOWuFjtkySqFpRnB1ovxZgSiwhhzhOBUe0x32Hx4Wp8ShB8lRv6ggho8gaRZC8BNPe1aLT5e46aRX8Bvfum_l2iHEm14Ew71osV1AhGMhX_YVIFc7Frfr2fWO-a0DxHdoalYfwqn4PHWa3xrsH8XWfIv_yHaFvFwHQNnBY7uo6mvn_9ZSpnkKjHjHpBpJXaBdXsP0E",
        quote: "The precision is unmatched in the industry. I've tried other tools, but Pikar stands out for its intuitive design."
    },
    {
        id: 3,
        name: "Elena Rodriguez",
        role: "Director of Ops",
        image: "https://lh3.googleusercontent.com/aida-public/AB6AXuByrG0REHIG2LlS16F3nnOF5wnRUT-ZmiPXiNxqAJolrpDYRULd3JQiIvLIUg96c0jnOXQ1ezHj-AaqbaFYJpAOgAWBrgeZSebpfuMZS9mSmulUHQh26cpPSrT-eEFWPOpGxD2GkJZKzw9EiCBknMwb3YrYNX6Rlg_Yq1iNL97VbE716iwM24gtsAU8LG9Wt5C6gJm-M-0l7tr8fQ46c1fZ-uGsJh8836epGjdCTUaB1xYizx-MPwHwQxpxvl5yqW42V4SxgV6adOA",
        quote: "Simply the best investment we made this year. It handles complex data processing like a charm."
    },
    {
        id: 4,
        name: "Michael Chang",
        role: "Senior Developer",
        image: "https://lh3.googleusercontent.com/aida-public/AB6AXuDfOoQvjLgwYcW9GQaBJG-mKNDziqXk-UPp2vcG51fy61BcVpTt4JwuDPi9GSZLRV87R1N7pDu7aG_gozHA0imir9-CNfX8oiF_w4N6nl48l5vcFRX20U7hHyiBkdiEtw1WEBWFEdv-y5KBCmRjX-xqHI3kClhg5loFV3hs17rPs3h-S7hUdx8nzj7XKOWyYVJOecVIyF4H5fUHYPkmJnmukXHuQWtAHvhb9qWklD2jOOLdBswlAAvg0gWZoSYr2N3c4uc5hvRUmqU",
        quote: "Incredible speed and accuracy for our needs. The API documentation is thorough and the support team is responsive."
    },
    {
        id: 5,
        name: "Lisa Ray",
        role: "UX Designer",
        image: "https://lh3.googleusercontent.com/aida-public/AB6AXuBZzg5neFZOtfQA5COdW7e9YQitXiAj98j2PejfyhCuvoOMgniAfiWnATQiJoVHBVcm1ks3VD7m22eIVTCWF5PO0pbcQfuuGZWB1lEgw8d-w26Ef02HPOtxHRI8ioNRVLVjcnwpoyExgZMzHUf8cl7EXqhapt7hx9eNKLeyOopQZL_eBIEVOecXTO2W25UdsSnF91kfHC0eoKmNa_mFu0WFelTrpC7ok-igjhhitZhZLRCMrD9fft9K--kx3Yr4hiBzOPq9kLnZN-A",
        quote: "A game changer for our design team. The asset generation features allow us to prototype 10x faster."
    },
    {
        id: 6,
        name: "James Wilson",
        role: "Founder at StartupX",
        image: "https://lh3.googleusercontent.com/aida-public/AB6AXuDXxYp4imBQ_1BNnm6KwDI7VGVOenXT7smmsruGwFEtFSZfnqgBOYd8vCgWc1DeFnF3UUx29w6rujfdKCV5iv-JFa-3L6CYM3i55rXpkUu9cQWvE28ZngnOvbQj8fwxjNdFQve55_DZZEcdb28zOhpdRnF-qUkbJxLlV1_xaVgYQ05rsDilGx240B9iTWGt6HDoMYoGZ_8q68eQzt6Gj2BS7vKqhZ2vMoMEhEsg7jTvlMXF_5M2jZq8bqHt4GoXRzoT5RsCq1NpuG0",
        quote: "Highly recommended for enterprise use. Security compliance was our main concern and Pikar nailed it."
    }
];
