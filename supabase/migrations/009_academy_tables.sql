-- EeshaMart Academy Schema
-- Run this in your Supabase SQL Editor

-- 1. COURSES TABLE
CREATE TABLE IF NOT EXISTS academy_courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    thumbnail_url TEXT,
    level VARCHAR(50) DEFAULT 'beginner', -- beginner, intermediate, advanced
    category VARCHAR(100),
    duration_minutes INTEGER DEFAULT 0,
    is_published BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id),
    order_index INTEGER DEFAULT 0
);

-- 2. LESSONS TABLE
CREATE TABLE IF NOT EXISTS academy_lessons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES academy_courses(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    video_url TEXT, -- YouTube, Vimeo, or direct video URL
    video_type VARCHAR(50) DEFAULT 'youtube', -- youtube, vimeo, direct
    duration_minutes INTEGER DEFAULT 0,
    order_index INTEGER DEFAULT 0,
    is_preview BOOLEAN DEFAULT false, -- Can watch without enrollment
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. LIVE SESSIONS TABLE
CREATE TABLE IF NOT EXISTS academy_live_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    thumbnail_url TEXT,
    host_name VARCHAR(255),
    scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_minutes INTEGER DEFAULT 60,
    room_name VARCHAR(255) UNIQUE, -- Jitsi room name
    is_live BOOLEAN DEFAULT false,
    is_completed BOOLEAN DEFAULT false,
    max_participants INTEGER DEFAULT 100,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id)
);

-- 4. SESSION REGISTRATIONS
CREATE TABLE IF NOT EXISTS academy_session_registrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES academy_live_sessions(id) ON DELETE CASCADE,
    seller_id UUID REFERENCES sellers(id) ON DELETE CASCADE,
    registered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    attended BOOLEAN DEFAULT false,
    UNIQUE(session_id, seller_id)
);

-- 5. COURSE ENROLLMENTS
CREATE TABLE IF NOT EXISTS academy_enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES academy_courses(id) ON DELETE CASCADE,
    seller_id UUID REFERENCES sellers(id) ON DELETE CASCADE,
    enrolled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    progress_percentage INTEGER DEFAULT 0,
    UNIQUE(course_id, seller_id)
);

-- 6. LESSON PROGRESS
CREATE TABLE IF NOT EXISTS academy_lesson_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id UUID REFERENCES academy_lessons(id) ON DELETE CASCADE,
    seller_id UUID REFERENCES sellers(id) ON DELETE CASCADE,
    completed BOOLEAN DEFAULT false,
    completed_at TIMESTAMP WITH TIME ZONE,
    watch_time_seconds INTEGER DEFAULT 0,
    UNIQUE(lesson_id, seller_id)
);

-- 7. CERTIFICATES
CREATE TABLE IF NOT EXISTS academy_certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES academy_courses(id) ON DELETE CASCADE,
    seller_id UUID REFERENCES sellers(id) ON DELETE CASCADE,
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    certificate_number VARCHAR(100) UNIQUE,
    UNIQUE(course_id, seller_id)
);

-- 8. QUIZZES
CREATE TABLE IF NOT EXISTS academy_quizzes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id UUID REFERENCES academy_lessons(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    options JSONB NOT NULL, -- ["Option 1", "Option 2", "Option 3", "Option 4"]
    correct_answer_index INTEGER NOT NULL, -- 0, 1, 2, or 3
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 9. QUIZ ATTEMPTS
CREATE TABLE IF NOT EXISTS academy_quiz_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id UUID REFERENCES academy_quizzes(id) ON DELETE CASCADE,
    seller_id UUID REFERENCES sellers(id) ON DELETE CASCADE,
    selected_answer_index INTEGER,
    is_correct BOOLEAN,
    attempted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 10. ACADEMY SETTINGS
CREATE TABLE IF NOT EXISTS academy_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default settings
INSERT INTO academy_settings (setting_key, setting_value) VALUES
    ('jitsi_domain', 'meet.jit.si'),
    ('certificate_template', 'default'),
    ('live_session_reminder_hours', '24')
ON CONFLICT (setting_key) DO NOTHING;

-- 11. ANNOUNCEMENTS
CREATE TABLE IF NOT EXISTS academy_announcements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    content TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE academy_courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE academy_lessons ENABLE ROW LEVEL SECURITY;
ALTER TABLE academy_live_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE academy_session_registrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE academy_enrollments ENABLE ROW LEVEL SECURITY;
ALTER TABLE academy_lesson_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE academy_certificates ENABLE ROW LEVEL SECURITY;
ALTER TABLE academy_quizzes ENABLE ROW LEVEL SECURITY;
ALTER TABLE academy_quiz_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE academy_announcements ENABLE ROW LEVEL SECURITY;

-- RLS Policies

-- Courses: Everyone can read published courses
CREATE POLICY "Courses are viewable by everyone" ON academy_courses
    FOR SELECT USING (is_published = true);

-- Lessons: Viewable if course is published
CREATE POLICY "Lessons viewable if course published" ON academy_lessons
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM academy_courses 
            WHERE academy_courses.id = academy_lessons.course_id 
            AND academy_courses.is_published = true
        )
    );

-- Live Sessions: Everyone can view
CREATE POLICY "Live sessions viewable by all" ON academy_live_sessions
    FOR SELECT USING (true);

-- Enrollments: Sellers can manage their own
CREATE POLICY "Sellers manage own enrollments" ON academy_enrollments
    FOR ALL USING (seller_id IN (SELECT id FROM sellers WHERE id = seller_id));

-- Lesson Progress: Sellers manage own progress
CREATE POLICY "Sellers manage own progress" ON academy_lesson_progress
    FOR ALL USING (seller_id IN (SELECT id FROM sellers WHERE id = seller_id));

-- Certificates: Sellers view own certificates
CREATE POLICY "Sellers view own certificates" ON academy_certificates
    FOR SELECT USING (seller_id IN (SELECT id FROM sellers WHERE id = seller_id));

-- Quizzes: Viewable if lesson's course is published
CREATE POLICY "Quizzes viewable if published" ON academy_quizzes
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM academy_lessons 
            JOIN academy_courses ON academy_courses.id = academy_lessons.course_id
            WHERE academy_lessons.id = academy_quizzes.lesson_id 
            AND academy_courses.is_published = true
        )
    );

-- Quiz Attempts: Sellers manage own
CREATE POLICY "Sellers manage own attempts" ON academy_quiz_attempts
    FOR ALL USING (seller_id IN (SELECT id FROM sellers WHERE id = seller_id));

-- Session Registrations: Sellers manage own
CREATE POLICY "Sellers manage own registrations" ON academy_session_registrations
    FOR ALL USING (seller_id IN (SELECT id FROM sellers WHERE id = seller_id));

-- Announcements: Everyone can view active
CREATE POLICY "Announcements viewable" ON academy_announcements
    FOR SELECT USING (is_active = true);

-- Admin policies (service role can do everything - for admin dashboard)
-- These will be handled via service role key in admin dashboard

-- Create index for better performance
CREATE INDEX IF NOT EXISTS idx_lessons_course_id ON academy_lessons(course_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_seller_id ON academy_enrollments(seller_id);
CREATE INDEX IF NOT EXISTS idx_progress_seller_id ON academy_lesson_progress(seller_id);
CREATE INDEX IF NOT EXISTS idx_sessions_scheduled ON academy_live_sessions(scheduled_at);
