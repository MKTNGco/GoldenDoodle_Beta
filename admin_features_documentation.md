
# GoldenDoodleLM Admin Features Documentation

## Table of Contents
1. [Account Creation](#account-creation)
2. [Company Account Management](#company-account-management)
3. [Team Member Management](#team-member-management)
4. [Friend Invitations](#friend-invitations)
5. [Admin User Panel](#admin-user-panel)
6. [Brand Voice Management](#brand-voice-management)
7. [Chat Interface Features](#chat-interface-features)
8. [Account Settings](#account-settings)

---

## Account Creation

### Individual Account Registration
1. **Visit Registration Page**: Navigate to `/register`
2. **Choose Account Type**: Select "Individual Account" for personal use
3. **Fill Required Information**:
   - First Name (required)
   - Last Name (required)
   - Email Address (required)
   - Password (required, minimum 8 characters)
4. **Select Subscription Plan**:
   - **Free**: Basic access with limited features
   - **Solo (The Practitioner)**: 1 brand voice, enhanced features
   - **Pro**: 10 brand voices, advanced capabilities
5. **Complete Registration**: 
   - For paid plans: Redirected to Stripe payment processing
   - For free plans: Email verification sent immediately
6. **Email Verification**: Check email and click verification link before signing in

### Company Account Registration
1. **Visit Registration Page**: Navigate to `/register`
2. **Choose Account Type**: Select "Company Account"
3. **Fill Required Information**:
   - First Name (required)
   - Last Name (required)
   - Email Address (required)
   - Password (required)
   - **Organization Name** (required for company accounts)
4. **Select Team Plan**:
   - **Team (The Organization)**: Up to 3 company brand voices
   - **Enterprise**: Up to 10 company brand voices
5. **Payment Processing**: Company accounts require paid subscriptions
6. **Admin Status**: First user becomes organization administrator automatically
7. **Email Verification**: Verify email before accessing features

### Beta/Invitation-Based Registration
- **Invitation Links**: Special registration flow for invited users
- **Beta Access**: 90-day free trial with team-level features
- **Organization Invitations**: Join existing company accounts via invite links

---

## Company Account Management

### Organization Structure
- **Tenant-Based System**: Each company is a separate tenant with isolated data
- **Admin Hierarchy**: Company administrators manage team members and settings
- **Brand Voice Limits**: Based on subscription level (Team: 3, Enterprise: 10)
- **User Roles**: Administrator or Member status

### Organization Settings Overview
- **Organization Name**: Display name for the company
- **Organization Type**: Company vs. Individual User designation
- **Brand Voice Allocation**: Shared pool managed by administrators
- **Member Management**: Admin-controlled user invitations and permissions

---

## Team Member Management

### Inviting Team Members (Admin Only)

#### From Account Page
1. **Navigate to Account**: Go to `/account`
2. **Access Team Management Tab**: Click "Team Management" tab (admin only)
3. **Click "Add Team Users"**: Button in Quick Actions or Team Management section
4. **Enter Email Address**: Type the new member's email
5. **Send Invitation**: System generates secure invitation token
6. **Email Delivery**: Invitation email sent with join link and organization details

#### From Admin Organization Panel
1. **Access Admin Panel**: Navigate to organization details
2. **Click "Invite Member"**: Use the invite button in the interface
3. **Enter Email**: Provide the team member's email address
4. **Send Invitation**: System processes and sends secure invitation

### Invitation Process Details
- **Token Generation**: Secure, time-limited invitation tokens
- **Email Template**: Professional invitation with organization name and inviting admin
- **Expiration**: Invitations expire after 7 days
- **Duplicate Prevention**: System prevents duplicate invitations to same email

### Managing Pending Invitations
- **View Pending Invites**: Admin panel shows all outstanding invitations
- **Invitation Status**: Track sent date, invited by, and recipient email
- **Auto-Refresh**: Pending invitations update when users accept

### Team Member Permissions
- **Member Role**: Standard access to chat, brand voices, and basic features
- **Admin Role**: User management, brand voice creation, billing oversight
- **Subscription Inheritance**: Team members inherit organizational subscription benefits

---

## Friend Invitations (Personal Network)

### Sending Friend Invitations

#### From Account Page
1. **Navigate to Account**: Go to `/account`
2. **Click "Tell Friends About Us"**: Located in Quick Actions section
3. **Add Email Addresses**: 
   - Enter emails separated by commas or new lines
   - Support for multiple recipients
4. **Select Relationship Type**:
   - Colleague
   - Friend  
   - Partner Organization
   - Other
5. **Add Personal Message**: Optional custom message included in invitation
6. **Send Invitations**: System generates unique invitation codes for each recipient

### Friend Invitation Features
- **Personal Referral Codes**: Each invitation gets unique tracking code
- **Email Customization**: Personal messages included in invitation emails
- **Invitation Statistics**: Track sent, accepted, and pending invitations
- **Relationship Tracking**: System tracks invitation source and type

### Viewing Invitation Statistics
- **Account Page Integration**: "My Invitations" tab shows comprehensive statistics
- **Metrics Displayed**:
  - Total Invitations Sent
  - Accepted Count
  - Pending Count
- **Detailed History**: View pending invitations with codes and send dates

---

## Admin User Panel

### Accessing Admin Features

#### Organization-Level Admin Panel
1. **Navigate to Account Page**: Go to `/account`
2. **Team Management Tab**: Available only for organization administrators
3. **Admin Controls**: Visible based on user permissions and organization type

#### Platform-Level Admin Panel (Super Admin Only)
1. **Access Platform Admin**: Navigate to `/platform-admin`
2. **User Management**: View all users across all organizations
3. **Organization Management**: Manage all tenants and their settings

### Admin Panel Features

#### User Management
- **View Active Users**: See all team members with details:
  - Name and email
  - Access level (Admin/Member)
  - Subscription level
  - Account status (Active/Pending)
  - Last login timestamp
  - Member since date
- **Update Subscriptions**: Admin can change user subscription levels
- **Remove Users**: Delete team members from organization

#### Pending Invitations Management
- **View Pending Invites**: See all outstanding invitations
- **Invitation Details**: Email, invited by, send date
- **Automatic Updates**: Real-time status updates when invitations are accepted

#### Organization Information
- **Organization Details**: Name, type, brand voice limits
- **Usage Statistics**: Current brand voice count vs. limits
- **Admin Information**: List of organization administrators

---

## Brand Voice Management

### Brand Voice Overview
Brand voices define your organization's communication style and personality. The system stores comprehensive brand identity information to ensure consistent messaging across all content generation.

### Creating a Brand Voice

#### Accessing the Brand Voice Wizard
1. **Navigate to Brand Voices**: Go to `/brand-voices`
2. **Click "Create Brand Voice"**: Available for admins and users within limits
3. **Brand Voice Wizard Opens**: Multi-step guided creation process

#### Step 1: Profile Setup (Required Fields)
**Company Information**:
- **Company Name** (required): Official organization name
- **Company URL** (required): Primary website address  
- **Voice Short Name** (required): Internal name for the brand voice

*Auto-save begins after these required fields are completed*

#### Step 2: Mission & Vision
**Mission Statement**: Core organizational purpose and values
**Vision Statement**: Future aspirations and long-term goals
**Core Values**: Fundamental principles guiding the organization
**Elevator Pitch**: Concise description of what the organization does
**About Us Content**: Detailed organizational background
**Press Release Boilerplate**: Standard company description for media

#### Step 3: Audience Definition
**Primary Audience Persona**: Detailed description of target audience
**Audience Pain Points**: Problems and challenges the audience faces
**Desired Relationship**: How the organization wants to connect with audience
**Audience Language**: Preferred communication style and terminology

#### Step 4: Brand Personality
**Personality Sliders** (1-5 scale):
- **Formal ↔ Casual**: Communication formality level
- **Serious ↔ Playful**: Tone and approach to messaging
- **Traditional ↔ Modern**: Contemporary vs. established approach  
- **Authoritative ↔ Collaborative**: Leadership vs. partnership style
- **Accessible ↔ Aspirational**: Approachable vs. exclusive positioning

**Personality Details**:
- **Brand as a Person**: If the brand were a person, describe their characteristics
- **Brand Spokesperson**: Ideal person to represent the brand
- **Admired Brands**: Organizations to emulate or learn from

#### Step 5: Language & Style Guidelines
**Word Choice**:
- **Words to Embrace**: Preferred terminology and language
- **Words to Avoid**: Language to exclude from communications

**Grammar & Punctuation**:
- **Contractions**: Use (don't, can't) or avoid (do not, cannot)
- **Oxford Comma**: Include or exclude serial commas
- **Additional Punctuation**: Special punctuation preferences

**Communication Style**:
- **Point of View**: First person plural (we/our), singular (I/my), or second person (you/your)
- **Sentence Structure**: Preferred sentence length and complexity

#### Step 6: Situational Responses
**Tone for Different Situations**:
- **Handling Good News**: Approach for positive announcements and celebrations
- **Handling Bad News/Apologies**: Strategy for addressing problems and mistakes

**Competitive Landscape**:
- **Main Competitors**: Key organizations in the same space
- **Competitor Communication Styles**: How competitors communicate
- **Voice Differentiation**: What makes this brand voice unique

### Auto-Save Functionality
The Brand Voice Wizard includes sophisticated auto-save capabilities:

#### Auto-Save Triggers
- **Input Changes**: Saves 2 seconds after user stops typing
- **Field Navigation**: Saves when moving between form fields
- **Step Changes**: Saves when navigating between wizard steps

#### Save Indicators
- **Visual Feedback**: Green checkmark appears when content is saved
- **Error Handling**: Warning indicator shows if save fails
- **Progress Recovery**: Users can resume where they left off

#### Draft Management
- **Local Storage Backup**: Drafts saved to browser storage
- **Session Recovery**: Auto-recover drafts up to 24 hours old
- **Profile ID Assignment**: Each draft gets unique identifier for tracking

### Brand Voice Storage Structure

#### Database Storage
All brand voice data is stored in tenant-specific database tables:
- **Configuration JSON**: All wizard responses stored as structured data
- **Markdown Content**: Generated comprehensive brand guide for AI context
- **Metadata**: Creation date, last modified, creator information

#### Generated Brand Guide Content
The system automatically generates a comprehensive markdown document including:
- Company overview and basic information
- Mission, vision, and values statements  
- Target audience analysis and pain points
- Detailed personality trait analysis
- Comprehensive language guidelines
- Situational response strategies
- Competitive differentiation points
- Trauma-informed communication principles

### Managing Existing Brand Voices

#### Editing Brand Voices
1. **Navigate to Brand Voices**: Go to `/brand-voices`
2. **Click "Edit" on Desired Voice**: Opens wizard in edit mode
3. **Make Changes**: All fields remain editable
4. **Auto-Save Active**: Changes saved automatically
5. **Update**: Final save updates the brand voice completely

#### Deleting Brand Voices
1. **Locate Brand Voice**: Find in brand voices list
2. **Click Delete Button**: Confirmation dialog appears
3. **Confirm Deletion**: Permanent removal from system
4. **Admin Only**: Only administrators can delete company brand voices

#### Brand Voice Limits
- **Solo Plan**: 1 personal brand voice
- **Pro Plan**: 10 personal brand voices  
- **Team Plan**: 3 company brand voices (shared)
- **Enterprise Plan**: 10 company brand voices (shared)

---

## Chat Interface Features

### Switching Between Brand Voices

#### Brand Voice Selection Process
1. **Access Chat Interface**: Navigate to `/chat`
2. **Locate Brand Voice Selector**: Dropdown menu in chat interface
3. **View Available Voices**: 
   - All company brand voices (for organization members)
   - Personal brand voices (if applicable)
   - "No Brand Voice" option available
4. **Select Desired Voice**: Click to activate for current conversation
5. **Visual Confirmation**: Selected brand voice appears in interface

#### Brand Voice Application
- **Conversation Context**: Selected brand voice applies to entire conversation
- **Switching Mid-Conversation**: Users can change brand voice during chat
- **Default Selection**: Interface remembers last used brand voice
- **No Brand Voice Option**: Users can generate content without brand voice constraints

### Content Mode Selection
Available content modes with brand voice integration:
- **Email**: Professional email generation with brand voice
- **Article**: Long-form content following brand guidelines  
- **Social Media**: Engaging posts reflecting brand personality
- **Rewrite**: Transform content using brand voice principles
- **Summarize**: Condense information maintaining brand tone
- **Brainstorm**: Creative ideation aligned with brand values
- **Analyze**: Data analysis with brand-appropriate presentation
- **Crisis**: Crisis communication following brand protocols

---

## Account Settings

### Profile Management

#### Personal Information Updates
1. **Navigate to Account**: Go to `/account`  
2. **Profile Tab**: View current information
3. **Click "Edit Profile"**: Opens profile editing modal
4. **Update Fields**:
   - First Name
   - Last Name  
   - Email Address
5. **Save Changes**: Updates applied immediately

#### Password Management
1. **Account Page**: Access from profile tab
2. **"Change Password" Button**: Opens password change modal
3. **Required Information**:
   - Current Password
   - New Password
   - Confirm New Password
4. **Security Validation**: Current password verified before change
5. **Confirmation**: Success message confirms password update

### Organization Settings (Admin Only)

#### Organization Information
- **Organization Name**: Display name for the company
- **Organization Type**: Company vs. Individual designation
- **Brand Voice Limits**: Current usage vs. maximum allowed
- **Admin Role Confirmation**: Current user's administrative status

#### Billing Information (Individual Users)
- **Current Plan**: Active subscription level
- **Brand Voice Allocation**: Usage limits based on plan
- **Account Deletion**: Permanent account removal option (individual users only)

### Account Deletion Process

#### Individual Account Deletion
1. **Navigate to Billing Tab**: Available for individual users only
2. **Locate "Danger Zone"**: Account deletion section
3. **Click "Delete Account"**: Opens confirmation modal
4. **Required Confirmations**:
   - Enter exact email address
   - Check confirmation checkbox
   - Optional: Provide deletion reason
5. **Final Confirmation**: Additional browser confirmation required
6. **Complete Deletion**: Account and all data permanently removed

#### Organization Member Limitations
- **No Self-Deletion**: Organization members cannot delete their own accounts
- **Admin Management**: Only organization admins can remove team members
- **Contact Admin**: System directs members to contact organization administrators

---

## System Features & Capabilities

### Data Security & Privacy
- **Tenant Isolation**: Each organization's data completely separated
- **Encryption**: All sensitive data encrypted in transit and at rest
- **Access Controls**: Role-based permissions enforce security boundaries
- **Audit Logging**: All administrative actions logged for security

### Auto-Save & Draft Recovery
- **Continuous Saving**: All forms auto-save progress every 2 seconds
- **Browser Storage**: Local backup prevents data loss
- **Session Recovery**: Resume interrupted work sessions
- **Error Handling**: Graceful handling of network interruptions

### Email Communications
- **Verification Emails**: Account activation and email changes
- **Invitation Emails**: Professional team and friend invitations  
- **Password Reset**: Secure password recovery process
- **Notification Emails**: Important account and organization updates

### Analytics & Tracking
- **Usage Metrics**: Track feature usage and engagement
- **Invitation Tracking**: Monitor invitation success rates
- **Performance Monitoring**: System health and response times
- **User Behavior**: Improve features based on usage patterns

---

## Troubleshooting Common Issues

### Account Access Issues
- **Email Verification**: Check spam folder for verification emails
- **Password Reset**: Use forgot password link if locked out
- **Organization Access**: Contact organization admin for permission issues

### Brand Voice Problems
- **Auto-Save Failures**: Check internet connection and retry
- **Draft Recovery**: Clear browser cache if drafts don't load
- **Wizard Navigation**: Complete required fields before advancing steps

### Team Management Issues
- **Invitation Delivery**: Check spam folders and email addresses
- **Permission Errors**: Verify admin status for management features
- **User Limits**: Upgrade subscription if hitting user or brand voice limits

### Technical Support
- **Contact Methods**: Email support or use in-app chat
- **Information to Provide**: Account email, organization name, specific error messages
- **Response Times**: Typical response within 24 hours for standard issues

---

*This documentation covers all administrative features in GoldenDoodleLM. For additional support or specific questions not covered here, please contact our support team.*
