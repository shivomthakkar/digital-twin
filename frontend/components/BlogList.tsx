import Link from 'next/link';

export default function BlogList({ blogs }: { blogs: any[] }) {
  return (
    <div className="mx-auto mt-10 grid max-w-2xl grid-cols-1 gap-x-8 gap-y-16 border-t border-gray-700 pt-10 sm:mt-16 sm:pt-16 lg:mx-0 lg:max-w-none lg:grid-cols-3">
      {blogs.map((post, idx) => (
        <article key={post.slug} className="flex max-w-xl flex-col items-start justify-between">
          <div className="flex items-center gap-x-4 text-xs">
            <time dateTime={post.frontmatter.date} className="text-gray-400">
              {new Date(post.frontmatter.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
            </time>
            <span className="relative z-10 rounded-full bg-gray-800/60 px-3 py-1.5 font-medium text-gray-300 hover:bg-gray-800">
              {post.frontmatter.category}
            </span>
          </div>
          <div className="group relative grow">
            <h3 className="mt-3 text-lg/6 font-semibold text-white group-hover:text-gray-300">
              <Link href={`/blogs/${post.slug}`}>
                <span className="absolute inset-0"></span>
                {post.frontmatter.title}
              </Link>
            </h3>
            <p className="mt-5 line-clamp-3 text-sm/6 text-gray-400">
              {post.frontmatter.excerpt || (post.contentHtml ? post.contentHtml.replace(/<[^>]+>/g, '').slice(0, 120) + '...' : '')}
            </p>
          </div>
        </article>
      ))}
    </div>
  );
}
