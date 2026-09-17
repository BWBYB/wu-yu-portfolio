import { getCollection } from 'astro:content';

export const projects = await getCollection('projects');
export const publishedProjects = projects.filter(({ data }) => data.status === 'published');
export const organizingProjects = projects.filter(({ data }) => data.status === 'organizing');
export const experiences = await getCollection('experiences');
export const posts = await getCollection('posts');

export function statusLabel(status: 'published' | 'organizing') {
	return status === 'published' ? '已发布' : '资料整理中';
}
