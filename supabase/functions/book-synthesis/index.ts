// Book Synthesis: Automatic content generation for book structure
// Takes extracted thought patterns and synthesizes them into structured book content

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from "npm:@supabase/supabase-js@2"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

interface SynthesisRequest {
  bookId?: string
  chapterIds?: string[]
  patternTypes?: string[]
  synthesisMode?: 'incremental' | 'comprehensive' | 'targeted'
  contentStyle?: 'academic' | 'narrative' | 'practical' | 'hybrid'
  minPatternConfidence?: number
  maxPatternsPerSection?: number
}

interface BookSection {
  id: string
  title: string
  level: number
  parentId?: string
  orderIndex: number
  currentContent: string
  targetWordCount: number
  currentWordCount: number
  completionPercentage: number
}

interface PatternMatch {
  patternId: string
  title: string
  type: string
  content: string
  confidence: number
  relevanceScore: number
  businessViability?: number
  technicalFeasibility?: number
  innovationScore?: number
}

serve(async (req) => {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const supabase = createClient({
      supabaseUrl: Deno.env.get('SUPABASE_URL') ?? '',
      supabaseServiceRoleKey: Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    })

    const { 
      bookId,
      chapterIds,
      patternTypes,
      synthesisMode = 'incremental',
      contentStyle = 'hybrid',
      minPatternConfidence = 0.7,
      maxPatternsPerSection = 10
    }: SynthesisRequest = await req.json()

    // Get book structure to work with
    let bookSections: BookSection[] = []
    
    if (bookId) {
      // Get all sections for specific book
      const { data: sections } = await supabase
        .from('book_structure')
        .select('*')
        .or(`id.eq.${bookId},parent_id.eq.${bookId}`)
        .order('level, order_index')
      
      bookSections = sections || []
    } else if (chapterIds && chapterIds.length > 0) {
      // Get specific chapters and their subsections
      const { data: sections } = await supabase
        .from('book_structure')
        .select('*')
        .or(`id.in.(${chapterIds.join(',')}),parent_id.in.(${chapterIds.join(',')})`)
        .order('level, order_index')
      
      bookSections = sections || []
    } else {
      // Get all incomplete sections (< 80% complete)
      const { data: sections } = await supabase
        .from('book_structure')
        .select('*')
        .lt('completion_percentage', 80)
        .gt('level', 1) // Skip root book level
        .order('level, order_index')
        .limit(5) // Process max 5 sections at a time
      
      bookSections = sections || []
    }

    if (bookSections.length === 0) {
      return new Response(
        JSON.stringify({ 
          success: true, 
          message: 'No sections need synthesis',
          processed: 0 
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const results = []
    let successCount = 0
    let errorCount = 0

    for (const section of bookSections) {
      try {
        console.log(`Synthesizing content for section: ${section.title}`)

        // Find relevant patterns for this section
        const relevantPatterns = await findRelevantPatterns(
          supabase,
          section,
          patternTypes,
          minPatternConfidence,
          maxPatternsPerSection
        )

        if (relevantPatterns.length === 0) {
          results.push({
            sectionId: section.id,
            title: section.title,
            status: 'skipped',
            reason: 'No relevant patterns found'
          })
          continue
        }

        // Generate enhanced content
        const synthesizedContent = await synthesizeContent(
          section,
          relevantPatterns,
          contentStyle,
          synthesisMode
        )

        // Update section with new content
        const updatedSection = await updateSectionContent(
          supabase,
          section,
          synthesizedContent,
          relevantPatterns.map(p => p.patternId)
        )

        results.push({
          sectionId: section.id,
          title: section.title,
          status: 'success',
          patternsUsed: relevantPatterns.length,
          wordCountBefore: section.currentWordCount,
          wordCountAfter: updatedSection.word_count,
          completionBefore: section.completionPercentage,
          completionAfter: updatedSection.completion_percentage
        })

        successCount++

      } catch (error) {
        console.error(`Error synthesizing section ${section.id}:`, error)
        results.push({
          sectionId: section.id,
          title: section.title,
          status: 'error',
          error: error.message
        })
        errorCount++
      }
    }

    console.log(`Book synthesis completed: ${successCount} success, ${errorCount} errors`)

    return new Response(
      JSON.stringify({
        success: true,
        summary: {
          sections_processed: bookSections.length,
          success: successCount,
          errors: errorCount,
          synthesis_mode: synthesisMode,
          content_style: contentStyle
        },
        results
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200
      }
    )

  } catch (error) {
    console.error('Function error:', error)
    return new Response(
      JSON.stringify({ 
        error: 'Internal server error',
        details: error.message 
      }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  }
})

// Find patterns relevant to a book section
async function findRelevantPatterns(
  supabase: any,
  section: BookSection,
  patternTypes?: string[],
  minConfidence: number = 0.7,
  maxPatterns: number = 10
): Promise<PatternMatch[]> {
  let query = supabase
    .from('thought_patterns')
    .select('*')
    .gte('confidence_score', minConfidence)

  // Filter by pattern types if specified
  if (patternTypes && patternTypes.length > 0) {
    query = query.in('pattern_type', patternTypes)
  }

  const { data: patterns } = await query
    .order('confidence_score', { ascending: false })
    .limit(maxPatterns * 3) // Get more to filter later

  if (!patterns || patterns.length === 0) {
    return []
  }

  // Calculate relevance scores based on section title and existing content
  const sectionKeywords = extractKeywords(section.title + ' ' + section.currentContent)
  
  const scoredPatterns = patterns.map(pattern => {
    const patternKeywords = pattern.keywords || []
    const patternThemes = pattern.themes || []
    
    // Calculate keyword overlap
    const keywordOverlap = sectionKeywords.filter(k => 
      patternKeywords.some((pk: string) => pk.toLowerCase().includes(k.toLowerCase())) ||
      patternThemes.some((pt: string) => pt.toLowerCase().includes(k.toLowerCase()))
    ).length

    const relevanceScore = Math.min(1.0, keywordOverlap / Math.max(sectionKeywords.length, 1))

    return {
      patternId: pattern.id,
      title: pattern.title,
      type: pattern.pattern_type,
      content: pattern.extracted_content,
      confidence: pattern.confidence_score,
      relevanceScore,
      businessViability: pattern.business_viability_score,
      technicalFeasibility: pattern.technical_feasibility_score,
      innovationScore: pattern.innovation_score
    }
  })

  // Sort by combined score (relevance + confidence) and return top matches
  return scoredPatterns
    .filter(p => p.relevanceScore > 0.1) // Minimum relevance threshold
    .sort((a, b) => (b.relevanceScore * 0.6 + b.confidence * 0.4) - (a.relevanceScore * 0.6 + a.confidence * 0.4))
    .slice(0, maxPatterns)
}

// Synthesize content using OpenAI
async function synthesizeContent(
  section: BookSection,
  patterns: PatternMatch[],
  contentStyle: string,
  synthesisMode: string
): Promise<string> {
  const openaiApiKey = Deno.env.get('OPENAI_API_KEY')
  if (!openaiApiKey) {
    throw new Error('OPENAI_API_KEY not configured')
  }

  // Prepare pattern summaries
  const patternSummaries = patterns.map(p => ({
    type: p.type,
    title: p.title,
    content: p.content.substring(0, 1000), // Limit length
    confidence: p.confidence,
    scores: {
      business: p.businessViability,
      technical: p.technicalFeasibility,
      innovation: p.innovationScore
    }
  }))

  // Determine synthesis approach based on mode
  const synthesisPrompts = {
    incremental: `Enhance the existing content by incorporating the provided thought patterns. Maintain the current structure and voice while weaving in relevant insights naturally.`,
    comprehensive: `Completely rewrite this section by synthesizing the provided thought patterns into a cohesive narrative. Create a comprehensive treatment of the topic.`,
    targeted: `Focus on specific aspects highlighted by the thought patterns. Update only the most relevant sections while preserving the overall structure.`
  }

  const styleGuides = {
    academic: `Use formal academic writing with proper citations, structured arguments, and scholarly tone. Include theoretical frameworks and empirical evidence.`,
    narrative: `Write in an engaging narrative style with storytelling elements, personal examples, and conversational tone that connects with readers.`,
    practical: `Focus on actionable insights, step-by-step guidance, and real-world applications. Use clear, direct language with concrete examples.`,
    hybrid: `Combine academic rigor with narrative engagement and practical applicability. Balance theory with examples and actionable insights.`
  }

  const systemPrompt = `You are an expert book editor and content synthesizer specializing in AI and knowledge management topics.

TASK: ${synthesisPrompts[synthesisMode as keyof typeof synthesisPrompts]}

STYLE: ${styleGuides[contentStyle as keyof typeof styleGuides]}

SECTION CONTEXT:
- Title: ${section.title}
- Level: ${section.level} (1=book, 2=chapter, 3=section, etc.)
- Target Word Count: ${section.targetWordCount}
- Current Word Count: ${section.currentWordCount}
- Current Content: ${section.currentContent}

SYNTHESIS REQUIREMENTS:
1. Incorporate insights from the provided thought patterns naturally
2. Maintain consistency with the book's overall theme and structure
3. Ensure content flows logically and builds on previous sections
4. Include specific examples and evidence from the patterns
5. Aim for the target word count while maintaining quality
6. Use clear headings and subheadings for readability
7. Reference pattern insights without explicitly citing them

OUTPUT FORMAT: Return only the synthesized markdown content for this section.`

  const userPrompt = `Synthesize content for this book section using the following thought patterns:

${JSON.stringify(patternSummaries, null, 2)}

Focus on creating cohesive, well-structured content that advances the book's narrative while incorporating the key insights from these patterns.`

  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${openaiApiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: 'gpt-4-turbo-preview',
      messages: [
        {
          role: 'system',
          content: systemPrompt
        },
        {
          role: 'user',
          content: userPrompt
        }
      ],
      temperature: 0.3,
      max_tokens: Math.min(4000, section.targetWordCount * 2) // Generous token limit
    })
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`OpenAI API error: ${response.status} - ${error}`)
  }

  const data = await response.json()
  const content = data.choices[0]?.message?.content

  if (!content) {
    throw new Error('No content generated from OpenAI')
  }

  return content.trim()
}

// Update section content in database
async function updateSectionContent(
  supabase: any,
  section: BookSection,
  newContent: string,
  sourcePatternIds: string[]
): Promise<any> {
  const { data: updatedSection, error } = await supabase
    .from('book_structure')
    .update({
      content: newContent,
      source_patterns: sourcePatternIds,
      updated_at: new Date().toISOString()
    })
    .eq('id', section.id)
    .select('*')
    .single()

  if (error) {
    throw new Error(`Failed to update section: ${error.message}`)
  }

  return updatedSection
}

// Extract keywords from text
function extractKeywords(text: string): string[] {
  // Simple keyword extraction - remove stop words and get significant terms
  const stopWords = new Set([
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
    'will', 'would', 'could', 'should', 'can', 'may', 'might', 'this', 'that', 'these', 'those'
  ])

  return text
    .toLowerCase()
    .split(/\W+/)
    .filter(word => word.length > 3 && !stopWords.has(word))
    .slice(0, 20) // Top 20 keywords
}

/*
Usage Examples:

1. Synthesize specific chapters:
POST /functions/v1/book-synthesis
{
  "chapterIds": ["chapter-uuid-1", "chapter-uuid-2"],
  "synthesisMode": "comprehensive",
  "contentStyle": "hybrid",
  "minPatternConfidence": 0.8
}

2. Incremental synthesis for incomplete sections:
POST /functions/v1/book-synthesis
{
  "synthesisMode": "incremental",
  "contentStyle": "practical",
  "patternTypes": ["technical-solution", "optimization-strategy"]
}

3. Full book synthesis:
POST /functions/v1/book-synthesis
{
  "bookId": "book-uuid",
  "synthesisMode": "comprehensive",
  "contentStyle": "academic",
  "maxPatternsPerSection": 15
}

Response:
{
  "success": true,
  "summary": {
    "sections_processed": 3,
    "success": 3,
    "errors": 0,
    "synthesis_mode": "comprehensive",
    "content_style": "hybrid"
  },
  "results": [
    {
      "sectionId": "section-uuid-1",
      "title": "Technical Patterns: Architecture and Problem-Solving",
      "status": "success",
      "patternsUsed": 8,
      "wordCountBefore": 1200,
      "wordCountAfter": 3400,
      "completionBefore": 15.0,
      "completionAfter": 42.5
    }
  ]
}
*/
