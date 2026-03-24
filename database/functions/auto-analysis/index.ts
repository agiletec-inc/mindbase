// Auto-Analysis: Automatic conversation analysis and pattern extraction
// Triggered by database events or manual requests to analyze conversations

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from "npm:@supabase/supabase-js@2"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

interface AnalysisRequest {
  conversationId?: string
  conversationIds?: string[]
  analysisType?: 'embedding' | 'pattern_extraction' | 'classification' | 'full_analysis'
  forceReanalysis?: boolean
}

interface OpenAIEmbeddingResponse {
  data: Array<{
    embedding: number[]
  }>
}

interface ThoughtPattern {
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
      conversationId, 
      conversationIds, 
      analysisType = 'full_analysis',
      forceReanalysis = false 
    }: AnalysisRequest = await req.json()

    // Determine which conversations to analyze
    let targetConversationIds: string[] = []
    
    if (conversationId) {
      targetConversationIds = [conversationId]
    } else if (conversationIds && Array.isArray(conversationIds)) {
      targetConversationIds = conversationIds
    } else {
      // Analyze pending conversations
      const { data: pendingJobs } = await supabase
        .from('conversation_analysis_jobs')
        .select('conversation_id')
        .eq('status', 'pending')
        .eq('job_type', analysisType)
        .limit(10)

      targetConversationIds = pendingJobs?.map(job => job.conversation_id) || []
    }

    if (targetConversationIds.length === 0) {
      return new Response(
        JSON.stringify({ 
          success: true, 
          message: 'No conversations to analyze',
          processed: 0 
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const results = []
    let successCount = 0
    let errorCount = 0

    for (const convId of targetConversationIds) {
      try {
        console.log(`Analyzing conversation: ${convId}`)

        // Update job status to processing
        await supabase
          .from('conversation_analysis_jobs')
          .update({ 
            status: 'processing', 
            started_at: new Date().toISOString(),
            progress_percentage: 0
          })
          .eq('conversation_id', convId)
          .eq('job_type', analysisType)

        // Get conversation data
        const { data: conversation, error: fetchError } = await supabase
          .from('conversations')
          .select('*')
          .eq('id', convId)
          .single()

        if (fetchError || !conversation) {
          throw new Error(`Failed to fetch conversation: ${fetchError?.message || 'Not found'}`)
        }

        let analysisResult: any = {}

        // Perform analysis based on type
        switch (analysisType) {
          case 'embedding':
            analysisResult = await generateEmbedding(conversation)
            break
          case 'pattern_extraction':
            analysisResult = await extractPatterns(conversation, supabase)
            break
          case 'classification':
            analysisResult = await classifyConversation(conversation)
            break
          case 'full_analysis':
          default:
            // Full analysis includes all steps
            const embeddingResult = await generateEmbedding(conversation)
            const classificationResult = await classifyConversation(conversation)
            const patternResult = await extractPatterns(conversation, supabase)
            
            analysisResult = {
              embedding: embeddingResult,
              classification: classificationResult,
              patterns: patternResult
            }
            break
        }

        // Update conversation with embedding if generated
        if (analysisResult.embedding) {
          await supabase
            .from('conversations')
            .update({ embedding: analysisResult.embedding })
            .eq('id', convId)
        }

        // Update job as completed
        await supabase
          .from('conversation_analysis_jobs')
          .update({
            status: 'completed',
            completed_at: new Date().toISOString(),
            progress_percentage: 100,
            result: analysisResult
          })
          .eq('conversation_id', convId)
          .eq('job_type', analysisType)

        results.push({
          conversationId: convId,
          status: 'success',
          analysisType,
          result: analysisResult
        })
        
        successCount++
        console.log(`Successfully analyzed conversation: ${convId}`)

      } catch (error) {
        console.error(`Error analyzing conversation ${convId}:`, error)
        
        // Update job as failed
        await supabase
          .from('conversation_analysis_jobs')
          .update({
            status: 'failed',
            error_message: error.message,
            completed_at: new Date().toISOString()
          })
          .eq('conversation_id', convId)
          .eq('job_type', analysisType)

        results.push({
          conversationId: convId,
          status: 'error',
          error: error.message
        })
        
        errorCount++
      }
    }

    console.log(`Analysis completed: ${successCount} success, ${errorCount} errors`)

    return new Response(
      JSON.stringify({
        success: true,
        summary: {
          total: targetConversationIds.length,
          success: successCount,
          errors: errorCount
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

// Generate OpenAI embeddings for conversation content
async function generateEmbedding(conversation: any): Promise<number[]> {
  const openaiApiKey = Deno.env.get('OPENAI_API_KEY')
  if (!openaiApiKey) {
    throw new Error('OPENAI_API_KEY not configured')
  }

  // Extract text content from conversation
  let textContent = ''
  
  if (conversation.raw_content) {
    textContent = conversation.raw_content
  } else if (conversation.content?.messages) {
    textContent = conversation.content.messages
      .map((msg: any) => msg.content || '')
      .join(' ')
  } else {
    textContent = JSON.stringify(conversation.content)
  }

  // Truncate if too long (OpenAI limit is ~8192 tokens)
  if (textContent.length > 30000) {
    textContent = textContent.substring(0, 30000) + '...'
  }

  const response = await fetch('https://api.openai.com/v1/embeddings', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${openaiApiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      input: textContent,
      model: 'text-embedding-ada-002'
    })
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`OpenAI API error: ${response.status} - ${error}`)
  }

  const data: OpenAIEmbeddingResponse = await response.json()
  return data.data[0].embedding
}

// Extract thought patterns from conversation
async function extractPatterns(conversation: any, supabase: any): Promise<ThoughtPattern[]> {
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
      .map((msg: any) => `${msg.role || 'unknown'}: ${msg.content || ''}`)
      .join('\n')
  }

  if (!conversationText.trim()) {
    return []
  }

  // Use OpenAI to extract patterns
  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${openaiApiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: 'gpt-4',
      messages: [
        {
          role: 'system',
          content: `You are an expert at analyzing conversations to extract recurring thought patterns, insights, and frameworks. 

Analyze the conversation and extract thought patterns. For each pattern, provide:
1. pattern_type: One of: business-idea, technical-solution, creative-concept, problem-analysis, architectural-design, optimization-strategy, learning-insight, decision-framework, workflow-improvement
2. title: Concise title (max 100 chars)
3. description: Brief description (max 200 chars)  
4. extracted_content: The actual content that represents this pattern
5. confidence_score: Your confidence in this pattern (0.0-1.0)
6. keywords: Array of relevant keywords
7. themes: Array of high-level themes
8. business_viability_score: Business potential (0.0-1.0, optional)
9. technical_feasibility_score: Technical feasibility (0.0-1.0, optional)
10. innovation_score: Innovation level (0.0-1.0, optional)

Return a JSON array of patterns. Only include significant, reusable patterns.`
        },
        {
          role: 'user',
          content: conversationText.substring(0, 15000) // Limit length
        }
      ],
      temperature: 0.3,
      max_tokens: 2000
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
      return []
    }

    // Store extracted patterns
    const validPatterns = patterns.filter(p => 
      p.pattern_type && p.title && p.extracted_content
    )

    for (const pattern of validPatterns) {
      // Generate embedding for pattern
      const embedding = await generateEmbedding({ raw_content: pattern.extracted_content })
      
      await supabase
        .from('thought_patterns')
        .insert({
          ...pattern,
          source_conversations: [conversation.id],
          embedding
        })
    }

    return validPatterns

  } catch (error) {
    console.error('Error parsing patterns:', error)
    return []
  }
}

// Classify conversation content
async function classifyConversation(conversation: any): Promise<any> {
  // Simple rule-based classification for now
  const content = conversation.raw_content || JSON.stringify(conversation.content)
  const lowerContent = content.toLowerCase()

  const classification = {
    primary_category: 'general',
    secondary_categories: [] as string[],
    technical_level: 'intermediate',
    business_relevance: 'medium',
    creativity_score: 0.5,
    complexity_score: 0.5
  }

  // Determine primary category
  if (lowerContent.includes('business') || lowerContent.includes('startup') || lowerContent.includes('revenue')) {
    classification.primary_category = 'business'
  } else if (lowerContent.includes('code') || lowerContent.includes('programming') || lowerContent.includes('api')) {
    classification.primary_category = 'technical'
  } else if (lowerContent.includes('design') || lowerContent.includes('creative') || lowerContent.includes('art')) {
    classification.primary_category = 'creative'
  } else if (lowerContent.includes('learn') || lowerContent.includes('education') || lowerContent.includes('explain')) {
    classification.primary_category = 'educational'
  }

  // Determine technical level
  const technicalKeywords = ['algorithm', 'architecture', 'framework', 'database', 'api', 'microservice']
  const advancedKeywords = ['optimization', 'scalability', 'distributed', 'machine learning', 'ai']
  
  if (advancedKeywords.some(keyword => lowerContent.includes(keyword))) {
    classification.technical_level = 'advanced'
  } else if (technicalKeywords.some(keyword => lowerContent.includes(keyword))) {
    classification.technical_level = 'intermediate'
  } else {
    classification.technical_level = 'beginner'
  }

  // Estimate complexity based on content length and vocabulary
  const wordCount = content.split(' ').length
  const uniqueWords = new Set(content.toLowerCase().split(/\W+/)).size
  
  classification.complexity_score = Math.min(1.0, (wordCount / 1000 + uniqueWords / 500) / 2)
  
  // Creativity score based on certain patterns
  const creativeKeywords = ['innovative', 'creative', 'novel', 'unique', 'original', 'idea']
  const creativeScore = creativeKeywords.filter(keyword => lowerContent.includes(keyword)).length / creativeKeywords.length
  classification.creativity_score = Math.min(1.0, creativeScore * 2)

  return classification
}

/*
Usage Examples:

1. Analyze specific conversation:
POST /functions/v1/auto-analysis
{
  "conversationId": "uuid-here",
  "analysisType": "full_analysis"
}

2. Analyze multiple conversations:
POST /functions/v1/auto-analysis
{
  "conversationIds": ["uuid1", "uuid2", "uuid3"],
  "analysisType": "embedding"
}

3. Process pending analysis jobs:
POST /functions/v1/auto-analysis
{
  "analysisType": "pattern_extraction"
}

Response:
{
  "success": true,
  "summary": {
    "total": 2,
    "success": 2,
    "errors": 0
  },
  "results": [
    {
      "conversationId": "uuid1",
      "status": "success",
      "analysisType": "full_analysis",
      "result": {
        "embedding": [0.1, -0.2, ...],
        "classification": {...},
        "patterns": [...]
      }
    }
  ]
}
*/
