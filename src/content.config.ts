import { glob } from 'astro/loaders';
import { defineCollection } from 'astro:content';
import { z } from 'astro/zod';

const status = z.enum(['published', 'organizing']);

const profile = defineCollection({
	loader: glob({ pattern: 'profile.md', base: './src/content' }),
	schema: z.object({
		title: z.string(),
		location: z.string(),
		graduation: z.number(),
		school: z.string(),
		major: z.string(),
		target: z.string(),
	}),
});

const projects = defineCollection({
	loader: glob({ pattern: '**/*.md', base: './src/content/projects' }),
	schema: z.object({
		title: z.string(),
		slug: z.string(),
		summary: z.string(),
		status,
		date: z.string(),
		category: z.string(),
		tags: z.array(z.string()),
		featured: z.boolean().default(false),
		externalUrl: z.url().optional(),
	}),
});

const experiences = defineCollection({
	loader: glob({ pattern: '**/*.md', base: './src/content/experiences' }),
	schema: z.object({
		title: z.string(),
		date: z.string(),
		location: z.string(),
		status,
		summary: z.string(),
	}),
});

const posts = defineCollection({
	loader: glob({ pattern: '**/*.md', base: './src/content/posts' }),
	schema: z.object({
		title: z.string(),
		slug: z.string(),
		date: z.string(),
		status,
		summary: z.string(),
		tags: z.array(z.string()),
	}),
});

export const collections = { profile, projects, experiences, posts };
