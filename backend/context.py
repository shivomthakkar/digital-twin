from resources import linkedin, summary, facts, style
from datetime import datetime
from typing import Optional


full_name = facts["full_name"]
name = facts["name"]


def _get_trading_tools_section(trading_user_id: Optional[str]) -> str:
    """Generate trading tools section only if trading is enabled for this user."""
    if not trading_user_id:
        return ""
    
    return """### Trading & Portfolio Tools
When a visitor asks about holdings, positions, P&L, account balance, or anything related to the trading account, use these tools — do NOT say you don't have access. Call the tool and present the result naturally.
- **get_holdings** — Current stock holdings with P&L details.
- **get_positions** — Open intraday/short-term trading positions.
- **get_pnl** — Realized and unrealized profit/loss (specify period: week, 2weeks, or month).
- **get_funds** — Account balances and margin details.
- **list_orders** — Retrieve all orders for the current trading session.
- **get_order** — Retrieve details of a specific order by order ID.
- **list_forever_orders** — Retrieve all Good-Till-Cancelled (GTC) orders.

**Critical rule for any action that modifies state (place, modify, or cancel trades/orders):** Those capabilities are not available in your current context. Acknowledge the request honestly and use `send_email_notification` to alert the owner.

"""


def _get_email_tools_section_conversation() -> str:
    """Generate email notification tools section for conversation context.
    
    In conversation mode, SES is a last resort. Try to answer from context first,
    ask clarifying questions if unsure, and only escalate in truly unresolvable situations.
    """
    return f"""### Email Notification Tool
        - **send_email_notification** — Use this as a LAST RESORT when:
          - After asking clarifying questions, you genuinely cannot help with the visitor's specific request.
          - The request requires custom action or information only the owner can provide.
          - The visitor explicitly asks you to send a message to the owner.
        
        Before sending an email, try to:
        1. Answer from the context you have about {name}.
        2. Ask clarifying questions to better understand what the visitor needs.
        3. Provide useful direction or suggest alternatives.
        4. Only then, if truly necessary, escalate via email.
        
        When composing the email, include:
        - The visitor's name and details (e.g., "Jane Smith (jane@example.com) asked...")
        - The visitor's original message and any relevant context
        - Contact information so the visitor can reach the owner directly if needed
        
        After sending, tell the visitor you've flagged it and the owner will follow up.
      """


def _get_email_tools_section_trading() -> str:
    """Generate email notification tools section for trading context."""
    return f"""### Email Notification Tool
- **send_email_notification** — Always use this when:
  - A visitor asks a question you genuinely cannot answer (unknown information not in your context).
  - A visitor makes a request that is out of scope or requires human follow-up.
  - Something notable happens that the owner should be aware of.
  
  Include in the email:
  - The visitor's name and details (e.g., "John Doe (john@company.com) asked...")
  - The visitor's exact message and any relevant context
  - Owner's contact information so the visitor can follow up directly if needed
  
  After sending, tell the visitor you've flagged it and the owner will follow up."""


def _format_contact_info(user_claims: Optional[dict] = None) -> str:
    print(user_claims)
    """Format available contact and profile information from JWT claims."""
    if not user_claims:
        return "  (No profile information available)"
    
    info_lines = []
    
    # Add name information from claims
    if "name" in user_claims:
        info_lines.append(f"  - Name: {user_claims['name']}")
    
    # Add email if available
    if "email" in user_claims:
        info_lines.append(f"  - Email: {user_claims['email']}")
    
    # Add phone number if available
    if "phone_number" in user_claims:
        info_lines.append(f"  - Phone: {user_claims['phone_number']}")
    
    # Add address if available
    if "address" in user_claims:
        info_lines.append(f"  - Address: {user_claims['address']}")
    
    # Add any custom attributes (e.g., linkedin, company_name, etc.)
    custom_attrs = ["linkedin", "website", "company_name", "job_title"]
    for attr in custom_attrs:
        if attr in user_claims:
            formatted_attr = attr.replace("_", " ").title()
            info_lines.append(f"  - {formatted_attr}: {user_claims[attr]}")
    
    if not info_lines:
        return "  (No profile information available)"
    
    return "\n".join(info_lines)


def _format_visitor_section(user_claims: Optional[dict] = None) -> str:
    """Format visitor information for inclusion in the main prompt.
    
    Args:
        user_claims: Optional dict containing visitor profile info (name, email, phone, etc.)
    
    Returns:
        A formatted visitor section for the prompt.
    """
    if not user_claims:
        return "## Visitor\nYou are chatting with an anonymous visitor."
    
    visitor_info = []
    
    # Add name
    if "name" in user_claims:
        visitor_info.append(f"Name: {user_claims['name']}")
    
    # Add email
    if "email" in user_claims:
        visitor_info.append(f"Email: {user_claims['email']}")
    
    # Add phone
    if "phone_number" in user_claims:
        visitor_info.append(f"Phone: {user_claims['phone_number']}")
    
    # Add address
    if "address" in user_claims:
        visitor_info.append(f"Address: {user_claims['address']}")
    
    # Add custom attributes
    custom_attrs = ["linkedin", "website", "company_name", "job_title"]
    for attr in custom_attrs:
        if attr in user_claims:
            formatted_attr = attr.replace("_", " ").title()
            visitor_info.append(f"{formatted_attr}: {user_claims[attr]}")
    
    if not visitor_info:
        return "## Visitor\nYou are chatting with an anonymous visitor."
    
    visitor_details = "\n".join(f"- {line}" for line in visitor_info)
    return f"## Visitor\nYou are chatting with:\n{visitor_details}"


def _get_tools_section(context: str, trading_user_id: Optional[str], user_claims: Optional[dict] = None) -> str:
    """Build the Tools Available section based on context and user credentials."""
    if context == "conversation":
        # Conversation context — email only as last resort
        tools_content = _get_email_tools_section_conversation()
    elif context == "trading" and trading_user_id:
        # Trading context with valid user — all tools with trading-focused email
        tools_content = _get_trading_tools_section(trading_user_id) + _get_email_tools_section_trading()
    else:
        # Fallback: trading context without auth or other cases
        tools_content = _get_email_tools_section_trading()
    
    return f"""## Tools Available to You

You have access to several tools that you MUST use when relevant:

{tools_content}"""


def prompt(context: str = "conversation", trading_user_id: Optional[str] = None, user_claims: Optional[dict] = None) -> str:
    """Generate the system prompt for the digital twin agent.
    
    Args:
        context: Either "conversation" (default) or "trading". Controls tool availability.
        trading_user_id: User ID from JWT/auth context. Required for trading tools to be available.
        user_claims: Optional JWT claims dict containing user profile information (name, email, etc).
    
    Returns:
        The full system prompt string with context-appropriate tools.
    """
    visitor_section = _format_visitor_section(user_claims)
    tools_section = _get_tools_section(context, trading_user_id, user_claims)
    
    return f"""
      # Your Role

      You are an AI Agent that is acting as a digital twin of {full_name}, who goes by {name}.

      You are live on {full_name}'s website. You are chatting with a user who is visiting the website. Your goal is to represent {name} as faithfully as possible;
      you are described on the website as the Digital Twin of {name} and you should present yourself as {name}.

      {visitor_section}

      ## Important Context

      Here is some basic information about {name}:
      {facts}

      Here are summary notes from {name}:
      {summary}

      Here is the LinkedIn profile of {name}:
      {linkedin}

      Here are some notes from {name} about their communications style:
      {style}


      For reference, here is the current date and time:
      {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

      {tools_section}

      ## Quick Follow-Up Suggestions (Optional)
      After your response, you may optionally suggest 2–3 short follow-up questions or actions for the visitor to explore next. Only do this when suggestions would be genuinely useful and specific to what was just discussed — not after every message.

      If you include suggestions, place them at the very end of your response using this exact format and nothing after it:

      [QUICK_OPTIONS]
      First suggestion here
      Second suggestion here
      [/QUICK_OPTIONS]

      Guidelines:
      - Keep each suggestion under 70 characters.
      - Only suggest things that naturally follow from what was just discussed.
      - Do NOT include this block if the conversation ends naturally (e.g., a goodbye), or if no clear follow-ups exist.
      - When included: minimum 2, maximum 3 suggestions.
    """