import { getBlogBySlug, getBlogSlugs } from '../../../lib/blogs';
import { notFound } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// Return a list of `params` to populate the [slug] dynamic segment
export async function generateStaticParams() {
	const slugs = [];
	for (const slug of getBlogSlugs()) {
		slugs.push({ slug: slug.replace(/\.md$/, '') });
	}
	return slugs;
}

interface BlogPageProps {
	params: { slug: string };
}

export default async function BlogPage({ params }: BlogPageProps) {
    const resolvedParams = await params;
	const blog = await getBlogBySlug(resolvedParams.slug);
	if (!blog) {
		notFound();
		return null;
	}
	const { frontmatter, content } = blog;
	return (
		<article className="mx-auto max-w-2xl py-10">
			<h1 className="text-3xl font-bold text-white mb-4">{frontmatter.title}</h1>
			<div className="flex items-center gap-x-4 text-xs mb-6">
				<time dateTime={frontmatter.date} className="text-gray-400">
					{new Date(frontmatter.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
				</time>
				<span className="relative z-10 rounded-full bg-gray-800/60 px-3 py-1.5 font-medium text-gray-300 hover:bg-gray-800">
					{frontmatter.category}
				</span>
			</div>
			<div className='prose prose-md text-justify'>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </div>
		</article>
        
	);
}
