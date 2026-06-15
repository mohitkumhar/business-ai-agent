import {
  defineCollection,
  defineConfig,
  suppressDeprecatedWarnings
} from '@content-collections/core'
import { compileMDX } from '@content-collections/mdx'
import {
  transformerMetaHighlight,
  transformerMetaWordHighlight,
  transformerNotationDiff
} from '@shikijs/transformers'
import rehypeAutolinkHeadings from 'rehype-autolink-headings'
import rehypePrettyCode from 'rehype-pretty-code'
import rehypeSlug from 'rehype-slug'
import remarkGfm from 'remark-gfm'
import type { Pluggable } from 'unified'
import { visit } from 'unist-util-visit'

suppressDeprecatedWarnings('legacySchema')

const posts = defineCollection({
  name: 'posts',
  directory: 'content',
  include: '**/*.mdx',
  schema: z => ({
    title: z.string(),
    description: z.string().optional(),
    postedAt: z.string().date().optional(),
    updatedAt: z.string().date().optional(),
    author: z.string(),
    cover: z.string().optional()
  }),
  transform: async (document, context) => {
    const mdx = await compileMDX(context, document, {
      remarkPlugins: [remarkGfm, remarkRemoveMdxExtension],
      rehypePlugins: [
        rehypeSlug,
        [rehypePrettyCode, rehypePrettyCodeSettings],
        [rehypeAutolinkHeadings, rehypeAutolinkHeadingsSettings]
      ]
    })
    return {
      ...document,
      mdx
    }
  }
})
export default defineConfig({
  collections: [posts]
})

type PrettyCodeNode = {
  children: Array<{ type: string; value?: string }>
  properties?: {
    className?: string[]
    [property: string]: unknown
  }
  [property: string]: unknown
}

function isPrettyCodeNode (node: unknown): node is PrettyCodeNode {
  return (
    typeof node === 'object' &&
    node !== null &&
    Array.isArray((node as PrettyCodeNode).children) &&
    (node as PrettyCodeNode).children.every(
      child =>
        typeof child === 'object' &&
        child !== null &&
        typeof (child as { type?: unknown }).type === 'string'
    )
  )
}

const rehypePrettyCodeSettings = {
  theme: 'material-theme-palenight',
  defaultLang: {
    block: 'md'
  },
  transformers: [
    transformerMetaHighlight(),
    transformerMetaWordHighlight(),
    transformerNotationDiff({
      matchAlgorithm: 'v3'
    })
  ],
  onVisitLine (node: unknown) {
    if (!isPrettyCodeNode(node)) {
      return
    }

    // Prevent lines from collapsing in `display: grid` mode, and allow empty
    // lines to be copy/pasted
    if (node.children.length === 0) {
      node.children = [{ type: 'text', value: ' ' }]
    }
  },
  onVisitHighlightedLine (node: unknown) {
    if (!isPrettyCodeNode(node) || !Array.isArray(node.properties?.className)) {
      return
    }

    node.properties.className.push('line--highlighted')
  },
  onVisitHighlightedWord (node: unknown) {
    if (!isPrettyCodeNode(node)) {
      return
    }

    node.properties = {
      ...node.properties,
      className: ['word--highlighted']
    }
  }
}

const rehypeAutolinkHeadingsSettings = {
  properties: {
    className: ['subheading-anchor'],
    ariaLabel: 'Link to section'
  }
}

const remarkRemoveMdxExtension: Pluggable = () => {
  return tree => {
    visit(tree, 'link', node => {
      const url = node.url as string
      if (
        typeof url === 'string' &&
        url.startsWith('./') &&
        url.endsWith('.mdx')
      ) {
        node.url = url.replace(/\.mdx$/, '')
      }
    })
  }
}
