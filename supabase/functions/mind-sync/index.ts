// Mind-Sync: Automatic conversation collection and synchronization
// Monitors local LLM conversation sources and auto-syncs to Supabase

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from "npm:@supabase/supabase-js@2"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

interface ConversationData {
  source: 'claude-desktop' | 'chatgpt' | 'cursor' | 'windsurf' | 'claude-code'
  sourceConversationId?: string
  title?: string
  content: any
  sourceCreatedAt?: string
  metadata?: Record<string, any>
}

interface SyncRequest {
  conversations: ConversationData[]
  sourceInfo?: {
    version?: string
    platform?: string
    timestamp?: string
  }
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

    const { conversations, sourceInfo }: SyncRequest = await req.json()

    if (!conversations || !Array.isArray(conversations)) {
      return new Response(
        JSON.stringify({ error: 'Invalid request: conversations array required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const results = []
    let successCount = 0
    let skipCount = 0
    let errorCount = 0

    for (const conv of conversations) {
      try {
        // Validate required fields
        if (!conv.source || !conv.content) {
          results.push({
            sourceConversationId: conv.sourceConversationId,
            status: 'error',
            error: 'Missing required fields: source and content'
          })
          errorCount++
          continue
        }

        // Check if conversation already exists
        const { data: existingConv } = await supabase
          .from('conversations')
          .select('id')
          .eq('source', conv.source)
          .eq('source_conversation_id', conv.sourceConversationId || '')
          .single()

        if (existingConv) {
          results.push({
            sourceConversationId: conv.sourceConversationId,
            status: 'skipped',
            reason: 'Already exists',
            conversationId: existingConv.id
          })
          skipCount++
          continue
        }

        // Prepare conversation data
        const conversationData = {
          source: conv.source,
          source_conversation_id: conv.sourceConversationId || null,
          title: conv.title || extractTitleFromContent(conv.content),
          content: conv.content,
          metadata: {
            ...conv.metadata,
            sync_source_info: sourceInfo,
            imported_at: new Date().toISOString()
          },
          source_created_at: conv.sourceCreatedAt || new Date().toISOString()
        }

        // Insert conversation
        const { data: newConv, error: insertError } = await supabase
          .from('conversations')
          .insert(conversationData)
          .select('id')
          .single()

        if (insertError) {
          console.error('Insert error:', insertError)
          results.push({
            sourceConversationId: conv.sourceConversationId,
            status: 'error',
            error: insertError.message
          })
          errorCount++
          continue
        }

        // Queue analysis job
        await supabase
          .from('conversation_analysis_jobs')
          .insert({
            conversation_id: newConv.id,
            job_type: 'full_analysis',
            status: 'pending'
          })

        results.push({
          sourceConversationId: conv.sourceConversationId,
          status: 'success',
          conversationId: newConv.id
        })
        successCount++

      } catch (error) {
        console.error('Processing error:', error)
        results.push({
          sourceConversationId: conv.sourceConversationId,
          status: 'error',
          error: error.message
        })
        errorCount++
      }
    }

    // Log sync summary
    console.log(`Sync completed: ${successCount} success, ${skipCount} skipped, ${errorCount} errors`)

    return new Response(
      JSON.stringify({
        success: true,
        summary: {
          total: conversations.length,
          success: successCount,
          skipped: skipCount,
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

// Helper function to extract title from conversation content
function extractTitleFromContent(content: any): string {
  try {
    // Handle different content formats
    if (typeof content === 'string') {
      // Plain text - use first 50 characters
      return content.substring(0, 50).trim() + (content.length > 50 ? '...' : '')
    }

    if (content.messages && Array.isArray(content.messages) && content.messages.length > 0) {
      // Message array format - use first user message
      const firstUserMessage = content.messages.find((msg: any) => 
        msg.role === 'user' || msg.role === 'human' || msg.sender === 'user'
      )
      
      if (firstUserMessage && firstUserMessage.content) {
        const text = typeof firstUserMessage.content === 'string' 
          ? firstUserMessage.content 
          : firstUserMessage.content.text || JSON.stringify(firstUserMessage.content)
        
        return text.substring(0, 50).trim() + (text.length > 50 ? '...' : '')
      }
    }

    if (content.title) {
      return content.title
    }

    if (content.topic) {
      return content.topic
    }

    // Fallback to JSON preview
    const jsonStr = JSON.stringify(content)
    return jsonStr.substring(0, 50).trim() + (jsonStr.length > 50 ? '...' : '')

  } catch (error) {
    console.error('Error extracting title:', error)
    return 'Untitled Conversation'
  }
}

/* 
Usage Examples:

1. Sync Claude Desktop conversations:
POST /functions/v1/mind-sync
{
  "conversations": [
    {
      "source": "claude-desktop",
      "sourceConversationId": "conv_123",
      "title": "Discussing React performance",
      "content": {
        "messages": [
          {"role": "user", "content": "How to optimize React performance?"},
          {"role": "assistant", "content": "Here are several strategies..."}
        ]
      },
      "sourceCreatedAt": "2024-12-17T12:00:00Z",
      "metadata": {
        "project": "web-optimization",
        "tags": ["react", "performance"]
      }
    }
  ],
  "sourceInfo": {
    "version": "1.0.0",
    "platform": "claude-desktop-mac",
    "timestamp": "2024-12-17T12:00:00Z"
  }
}

2. Sync multiple conversations in batch:
POST /functions/v1/mind-sync
{
  "conversations": [
    {...conversation1...},
    {...conversation2...},
    {...conversation3...}
  ]
}

Response:
{
  "success": true,
  "summary": {
    "total": 3,
    "success": 2,
    "skipped": 1,
    "errors": 0
  },
  "results": [
    {
      "sourceConversationId": "conv_123",
      "status": "success",
      "conversationId": "uuid-here"
    },
    {
      "sourceConversationId": "conv_124", 
      "status": "skipped",
      "reason": "Already exists"
    }
  ]
}
*/
