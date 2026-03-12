import fs from 'fs';
import path from 'path';
import matter from 'gray-matter';
import remarkParse from 'remark-parse';
import remarkHtml from 'remark-html';
import {unified} from 'unified';

const blogsDirectory = path.join(process.cwd(), 'public/content/blogs');

export function getBlogSlugs(): string[] {
  return fs.readdirSync(blogsDirectory).filter(file => file.endsWith('.md'));
}

export async function getBlogBySlug(slug: string) {
  if (!slug || typeof slug !== 'string') return null;
  const realSlug = slug.replace(/\.md$/, '');
  const fullPath = path.join(blogsDirectory, `${realSlug}.md`);
  if (!fs.existsSync(fullPath)) return null;
  const fileContents = fs.readFileSync(fullPath, 'utf8');
  const { data, content } = matter(fileContents);
  const processedContent = await unified().use(remarkParse).use(remarkHtml).process(content);
  const contentHtml = processedContent.toString();
  return {
    slug: realSlug,
    frontmatter: data,
    contentHtml,
    content
  };
}

export async function getAllBlogs() {
  const slugs = getBlogSlugs();
  const blogs = await Promise.all(slugs.map(slug => getBlogBySlug(slug)));
  return blogs.sort((a, b) => (a?.frontmatter.date < b?.frontmatter.date ? 1 : -1));
}
