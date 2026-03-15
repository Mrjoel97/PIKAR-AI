import { fetchWithAuth } from './api';

export interface CommunityPost {
  id: string;
  user_id: string;
  author_name: string;
  title: string;
  body: string;
  category: string;
  tags: string[];
  upvotes: number;
  reply_count: number;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
}

export interface CommunityComment {
  id: string;
  post_id: string;
  user_id: string;
  author_name: string;
  body: string;
  upvotes: number;
  created_at: string;
}

export async function listPosts(params?: {
  category?: string;
  sort?: 'recent' | 'popular';
  limit?: number;
  offset?: number;
}): Promise<CommunityPost[]> {
  const qs = new URLSearchParams();
  if (params?.category) qs.set('category', params.category);
  if (params?.sort) qs.set('sort', params.sort);
  if (params?.limit) qs.set('limit', String(params.limit));
  if (params?.offset) qs.set('offset', String(params.offset));
  const query = qs.toString();
  const response = await fetchWithAuth(`/community/posts${query ? `?${query}` : ''}`);
  return response.json();
}

export async function createPost(data: {
  title: string;
  body: string;
  category?: string;
  tags?: string[];
}): Promise<CommunityPost> {
  const response = await fetchWithAuth('/community/posts', {
    method: 'POST',
    body: JSON.stringify(data),
  });
  return response.json();
}

export async function getPost(postId: string): Promise<{ post: CommunityPost; comments: CommunityComment[] }> {
  const response = await fetchWithAuth(`/community/posts/${postId}`);
  return response.json();
}

export async function addComment(postId: string, body: string): Promise<CommunityComment> {
  const response = await fetchWithAuth(`/community/posts/${postId}/comments`, {
    method: 'POST',
    body: JSON.stringify({ body }),
  });
  return response.json();
}

export async function toggleUpvote(postId: string): Promise<{ upvoted: boolean; upvotes: number }> {
  const response = await fetchWithAuth(`/community/posts/${postId}/upvote`, {
    method: 'POST',
  });
  return response.json();
}
