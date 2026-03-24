// Pattern Extraction: Advanced thought pattern analysis and categorization
// Specialized function for extracting detailed patterns from conversations

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from "npm:@supabase/supabase-js@2"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

interface PatternExtractionRequest {
  conversationIds?: string[]
  patternTypes?: string[]
  minConfidence?: number
  includeExisting?: boolean
  analysisDepth?: 'quick' | 'standard' | 'deep'
}

interface ExtractedPattern {
  pattern_type: string
  title: string
  description: string
  extracted_content: string
  confidence_score: number
  keywords: string[]
  themes: string[]
  business_viability_score?: number
  technical_feasibility_score?: number
  innovation_score?: number
  source_conversation_id: string
  related_patterns?: string[]
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
      conversationIds,
      patternTypes,
      minConfidence = 0.6,
      includeExisting = false,
      analysisDepth = 'standard'
    }: PatternExtractionRequest = await req.json()

    // Get conversations to analyze
    let conversations: any[] = []
    
    if (conversationIds && conversationIds.length > 0) {
      const { data } = await supabase
        .from('conversations')
        .select('*')
        .in('id', conversationIds)
      conversations = data || []
    } else {
      // Get recent conversations that haven't been analyzed for patterns
      const { data } = await supabase
        .from('conversations')
        .select(`
          *,
          thought_patterns!inner(id)
        `)
        .gte('created_at', new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()) // Last 7 days
        .limit(20)
      
      conversations = includeExisting ? data || [] : (data || []).filter(conv => conv.thought_patterns.length === 0)
    }

    if (conversations.length === 0) {
      return new Response(
        JSON.stringify({ 
          success: true, 
          message: 'No conversations to analyze',
          patterns: [] 
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const allPatterns: ExtractedPattern[] = []
    const results = []

    for (const conversation of conversations) {
      try {
        console.log(`Extracting patterns from conversation: ${conversation.id}`)

        const patterns = await extractAdvancedPatterns(
          conversation, 
          analysisDepth,
          patternTypes,
          minConfidence
        )

        for (const pattern of patterns) {
          // Generate embedding for pattern
          const embedding = await generateEmbedding(pattern.extracted_content)
          
          // Insert pattern into database
          const { data: insertedPattern, error } = await supabase
            .from('thought_patterns')
            .insert({
              pattern_type: pattern.pattern_type,
              title: pattern.title,
              description: pattern.description,
              extracted_content: pattern.extracted_content,
              source_conversations: [conversation.id],
              confidence_score: pattern.confidence_score,
              keywords: pattern.keywords,
              themes: pattern.themes,
              business_viability_score: pattern.business_viability_score,
              technical_feasibility_score: pattern.technical_feasibility_score,
              innovation_score: pattern.innovation_score,
              embedding
            })
            .select()
            .single()

          if (!error && insertedPattern) {
            allPatterns.push({
              ...pattern,
              source_conversation_id: conversation.id
            })
          } else {
            console.error('Error inserting pattern:', error)
          }
        }

        results.push({
          conversationId: conversation.id,
          patternsExtracted: patterns.length,
          status: 'success'
        })

      } catch (error) {
        console.error(`Error extracting patterns from conversation ${conversation.id}:`, error)
        results.push({
          conversationId: conversation.id,
          status: 'error',
          error: error.message
        })
      }
    }

    // Find cross-conversation patterns
    const crossPatterns = await findCrossConversationPatterns(allPatterns)

    console.log(`Pattern extraction completed: ${allPatterns.length} patterns extracted`)

    return new Response(
      JSON.stringify({
        success: true,
        summary: {
          conversations_analyzed: conversations.length,
          patterns_extracted: allPatterns.length,
          cross_patterns_found: crossPatterns.length
        },
        patterns: allPatterns,
        cross_patterns: crossPatterns,
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

// Advanced pattern extraction using OpenAI
async function extractAdvancedPatterns(
  conversation: any,
  depth: string,
  targetTypes?: string[],
  minConfidence: number = 0.6
): Promise<ExtractedPattern[]> {
  const openaiApiKey = Deno.env.get('OPENAI_API_KEY')
  if (!openaiApiKey) {
    throw new Error('OPENAI_API_KEY not configured')
  }

  // Extract conversation text
  let conversationText = ''
  if (conversation.raw_content) {
    conversationText = conversation.raw_content
  } else if (conversation.content?.messages) {
    conversationText = conversation.content.messages
      .map((msg: any) => `${msg.role || 'speaker'}: ${msg.content || ''}`)
      .join('\n\n')
  }

  if (!conversationText.trim()) {
    return []
  }

  // Determine analysis prompts based on depth
  const systemPrompts = {
    quick: `Extract the top 2-3 most significant thought patterns from this conversation. Focus on clear, actionable insights.`,
    standard: `Analyze this conversation to extract meaningful thought patterns. Look for recurring themes, problem-solving approaches, decision frameworks, and innovative ideas.`,
    deep: `Perform comprehensive pattern analysis. Extract all significant thought patterns including subtle frameworks, implicit decision-making processes, creative approaches, and meta-cognitive strategies. Consider both explicit statements and implied methodologies.`
  }

  const analysisInstructions = `
${systemPrompts[depth as keyof typeof systemPrompts]}

Pattern Types (use these exact values):
- business-idea: Business concepts, revenue models, market opportunities
- technical-solution: Technical approaches, architectural patterns, problem-solving methods
- creative-concept: Creative ideas, artistic approaches, innovative thinking
- problem-analysis: Problem decomposition, root cause analysis, systematic investigation
- architectural-design: System design, structural thinking, scalability approaches
- optimization-strategy: Performance improvements, efficiency methods, resource optimization
- learning-insight: Knowledge acquisition patterns, learning strategies, educational approaches
- decision-framework: Decision-making processes, evaluation criteria, trade-off analysis
- workflow-improvement: Process optimization, productivity methods, organizational strategies

For each pattern, provide:
1. pattern_type: Use exact values from above list
2. title: Concise, descriptive title (max 80 characters)
3. description: Clear explanation of the pattern (max 200 characters)
4. extracted_content: The actual content that exemplifies this pattern (be specific)
5. confidence_score: Your confidence in this pattern (0.0-1.0, only include if >= ${minConfidence})
6. keywords: Array of 3-8 relevant keywords
7. themes: Array of 2-5 high-level themes
8. business_viability_score: Commercial potential (0.0-1.0, null if not applicable)
9. technical_feasibility_score: Implementation difficulty (0.0-1.0, null if not applicable)
10. innovation_score: Novelty and creativity level (0.0-1.0)

${targetTypes ? `Focus specifically on these pattern types: ${targetTypes.join(', ')}` : ''}

Return only a JSON array of patterns. Each pattern must have confidence_score >= ${minConfidence}.`

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
          content: analysisInstructions
        },
        {
          role: 'user',
          content: conversationText.substring(0, depth === 'deep' ? 20000 : depth === 'standard' ? 15000 : 10000)
        }
      ],
      temperature: 0.2,
      max_tokens: depth === 'deep' ? 3000 : depth === 'standard' ? 2000 : 1000
    })
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`OpenAI API error: ${response.status} - ${error}`)
  }

  const data = await response.json()
  const content = data.choices[0]?.message?.content

  if (!content) {
    return []
  }

  try {
    const patterns = JSON.parse(content)
    if (!Array.isArray(patterns)) {
      console.error('OpenAI returned non-array response:', content)
      return []
    }

    // Validate and filter patterns
    return patterns.filter(pattern => {
      return pattern.pattern_type && 
             pattern.title && 
             pattern.extracted_content &&
             pattern.confidence_score >= minConfidence &&
             (!targetTypes || targetTypes.includes(pattern.pattern_type))
    })

  } catch (error) {
    console.error('Error parsing patterns from OpenAI response:', error)
    console.error('Raw response:', content)
    return []
  }
}

// Find patterns that appear across multiple conversations
async function findCrossConversationPatterns(patterns: ExtractedPattern[]): Promise<any[]> {
  const crossPatterns = []
  
  // Group patterns by type and keywords
  const patternGroups: { [key: string]: ExtractedPattern[] } = {}
  
  for (const pattern of patterns) {
    const key = `${pattern.pattern_type}:${pattern.keywords.slice(0, 2).sort().join(',')}`
    if (!patternGroups[key]) {
      patternGroups[key] = []
    }
    patternGroups[key].push(pattern)
  }

  // Find groups with multiple patterns from different conversations
  for (const [groupKey, groupPatterns] of Object.entries(patternGroups)) {
    if (groupPatterns.length >= 2) {
      const uniqueConversations = new Set(groupPatterns.map(p => p.source_conversation_id))
      
      if (uniqueConversations.size >= 2) {
        crossPatterns.push({
          pattern_group: groupKey,
          occurrences: groupPatterns.length,
          conversations: Array.from(uniqueConversations),
          average_confidence: groupPatterns.reduce((sum, p) => sum + p.confidence_score, 0) / groupPatterns.length,
          common_themes: findCommonElements(groupPatterns.map(p => p.themes)),
          common_keywords: findCommonElements(groupPatterns.map(p => p.keywords)),
          examples: groupPatterns.slice(0, 3) // Top 3 examples
        })
      }
    }
  }

  return crossPatterns.sort((a, b) => b.occurrences - a.occurrences)
}

// Helper function to find common elements across arrays
function findCommonElements(arrays: string[][]): string[] {
  if (arrays.length === 0) return []
  
  const elementCounts: { [key: string]: number } = {}
  
  for (const array of arrays) {
    const uniqueElements = new Set(array)
    for (const element of uniqueElements) {
      elementCounts[element] = (elementCounts[element] || 0) + 1
    }
  }

  // Return elements that appear in at least 50% of arrays
  const threshold = Math.ceil(arrays.length / 2)
  return Object.entries(elementCounts)
    .filter(([_, count]) => count >= threshold)
    .map(([element, _]) => element)
}

// Generate embeddings for pattern content
async function generateEmbedding(content: string): Promise<number[]> {
  const openaiApiKey = Deno.env.get('OPENAI_API_KEY')
  if (!openaiApiKey) {
    throw new Error('OPENAI_API_KEY not configured')
  }

  // Truncate if too long
  if (content.length > 8000) {
    content = content.substring(0, 8000) + '...'
  }

  const response = await fetch('https://api.openai.com/v1/embeddings', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${openaiApiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      input: content,
      model: 'text-embedding-ada-002'
    })
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`OpenAI API error: ${response.status} - ${error}`)
  }

  const data = await response.json()
  return data.data[0].embedding
}

/*
Usage Examples:

1. Extract patterns from specific conversations:
POST /functions/v1/pattern-extraction
{
  "conversationIds": ["uuid1", "uuid2"],
  "analysisDepth": "deep",
  "minConfidence": 0.7
}

2. Extract only business-related patterns:
POST /functions/v1/pattern-extraction
{
  "patternTypes": ["business-idea", "optimization-strategy"],
  "minConfidence": 0.8
}

3. Quick analysis of recent conversations:
POST /functions/v1/pattern-extraction
{
  "analysisDepth": "quick",
  "includeExisting": false
}

Response:
{
  "success": true,
  "summary": {
    "conversations_analyzed": 5,
    "patterns_extracted": 23,
    "cross_patterns_found": 4
  },
  "patterns": [...],
  "cross_patterns": [
    {
      "pattern_group": "technical-solution:optimization,performance",
      "occurrences": 3,
      "conversations": ["uuid1", "uuid2", "uuid3"],
      "average_confidence": 0.85,
      "common_themes": ["performance", "scalability"],
      "examples": [...]
    }
  ]
}
*/
