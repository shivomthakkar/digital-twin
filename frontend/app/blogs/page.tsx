import BlogList from '../../components/BlogList';
import { getAllBlogs } from '../../lib/blogs';

export default async function Blogs() {
  const blogs = await getAllBlogs();
  return (
    <div className="bg-gray-900 py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl lg:mx-0">
          <h2 className="text-4xl font-semibold tracking-tight text-pretty text-white sm:text-5xl">From the blog</h2>
          <p className="mt-2 text-lg/8 text-gray-300">My experiences in the world of technology and software development.</p>
          </div>
          <BlogList blogs={blogs} />
      </div>
    </div>
  );
}
