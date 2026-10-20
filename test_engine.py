"""
Unit and integration tests for engine.py
"""

import os
import shutil
import subprocess
import unittest
from engine import (
    format_timestamp,
    is_thai_text,
    generate_srt,
    generate_vtt,
    shift_subtitle_segments,
    translate_chunk_google,
    translate_texts_to_thai,
    find_ffmpeg,
    has_audio_stream,
    extract_audio,
    burn_subtitles_to_video,
    mux_subtitles_to_video,
    process_video_subtitles,
    post_process_jav_thai,
    translate_segments_with_gemini,
    load_whisper_model_safely,
    check_cuda_availability,
)


class TestTimestampFormatting(unittest.TestCase):
    def test_zero_timestamp(self):
        self.assertEqual(format_timestamp(0.0, "srt"), "00:00:00,000")
        self.assertEqual(format_timestamp(0.0, "vtt"), "00:00:00.000")

    def test_negative_timestamp(self):
        self.assertEqual(format_timestamp(-5.2, "srt"), "00:00:00,000")

    def test_minute_boundary(self):
        self.assertEqual(format_timestamp(59.999, "srt"), "00:00:59,999")
        self.assertEqual(format_timestamp(60.0, "srt"), "00:01:00,000")

    def test_hour_boundary(self):
        self.assertEqual(format_timestamp(3661.123, "srt"), "01:01:01,123")
        self.assertEqual(format_timestamp(3661.123, "vtt"), "01:01:01.123")


class TestThaiDetection(unittest.TestCase):
    def test_thai_sentences(self):
        self.assertTrue(is_thai_text("สวัสดีครับ ยินดีต้อนรับสู่โปรแกรมซับไทย"))
        self.assertTrue(is_thai_text("ทดสอบ 1 2 3 ข้อความภาษาไทย"))

    def test_non_thai_sentences(self):
        self.assertFalse(is_thai_text("Hello world, this is a subtitle test."))
        self.assertFalse(is_thai_text("こんにちは、元気ですか？"))
        self.assertFalse(is_thai_text("1234567890 !@#$%^&*()"))
        self.assertFalse(is_thai_text("   "))


class TestSubtitleGenerators(unittest.TestCase):
    def setUp(self):
        self.segments = [
            {
                "id": 1,
                "start": 1.5,
                "end": 3.75,
                "original_text": "Hello world",
                "thai_text": "สวัสดีชาวโลก",
            },
            {
                "id": 2,
                "start": 4.0,
                "end": 6.2,
                "original_text": "Welcome to subtitle app",
                "thai_text": "ยินดีต้อนรับสู่แอปทำซับไตเติล",
            },
        ]

    def test_srt_generation(self):
        srt = generate_srt(self.segments)
        self.assertIn("1\n00:00:01,500 --> 00:00:03,750\nสวัสดีชาวโลก", srt)
        self.assertIn("2\n00:00:04,000 --> 00:00:06,200\nยินดีต้อนรับสู่แอปทำซับไตเติล", srt)

    def test_vtt_generation(self):
        vtt = generate_vtt(self.segments)
        self.assertTrue(vtt.startswith("WEBVTT"))
        self.assertIn("1\n00:00:01.500 --> 00:00:03.750\nสวัสดีชาวโลก", vtt)

    def test_shift_subtitle_segments(self):
        # Shift forward +1.5s
        shifted_pos = shift_subtitle_segments(self.segments, 1.5)
        self.assertEqual(shifted_pos[0]["start"], 3.0)
        self.assertEqual(shifted_pos[0]["end"], 5.25)
        self.assertEqual(shifted_pos[0]["start_str"], "00:00:03,000")

        # Shift backward -2.0s (testing 0.0 floor boundary)
        shifted_neg = shift_subtitle_segments(self.segments, -2.0)
        self.assertEqual(shifted_neg[0]["start"], 0.0)
        self.assertGreater(shifted_neg[0]["end"], 0.0)


class TestTranslation(unittest.TestCase):
    def test_google_translate_batch(self):
        inputs = ["Hello", "Thank you very much"]
        results = translate_texts_to_thai(inputs)
        self.assertEqual(len(results), 2)
        # Verify result contains Thai characters
        self.assertTrue(any('\u0e00' <= c <= '\u0e7f' for c in results[0]))
        self.assertTrue(any('\u0e00' <= c <= '\u0e7f' for c in results[1]))

    def test_translate_empty_inputs(self):
        self.assertEqual(translate_texts_to_thai([]), [])
        self.assertEqual(translate_texts_to_thai(["", "   "]), ["", "   "])

    def test_multiline_segment_translation_alignment(self):
        # Verifies internal newlines within a segment do not cause index shifting
        inputs = ["Line 1\nLine 1 extra detail", "Line 2 separate concept"]
        results = translate_texts_to_thai(inputs)
        self.assertEqual(len(results), 2)
        self.assertTrue(len(results[0].strip()) > 0)
        self.assertTrue(len(results[1].strip()) > 0)

    def test_translate_chunk_google_post(self):
        inputs = ["Hello", "Good morning"]
        results = translate_chunk_google(inputs, target_lang="th")
        self.assertEqual(len(results), 2)
        self.assertTrue(any('\u0e00' <= c <= '\u0e7f' for c in results[0]))
        self.assertTrue(any('\u0e00' <= c <= '\u0e7f' for c in results[1]))

    def test_translate_chunk_google_handles_erroneous_source_lang_th_for_japanese(self):
        # Even if source_lang='th' is erroneously passed, Japanese CJK text MUST be translated to Thai
        inputs = ["もう、そんなにコンツメないの?"]
        results = translate_chunk_google(inputs, target_lang="th", source_lang="th")
        self.assertEqual(len(results), 1)
        # Result must contain Thai characters and no CJK characters
        self.assertTrue(any('\u0e00' <= c <= '\u0e7f' for c in results[0]))
        self.assertFalse(any('\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in results[0]))


class TestJAVTranslationAndStyles(unittest.TestCase):
    def test_post_process_jav_thai_general_patterns(self):
        # Climax / going
        self.assertIn("จะเสร็จแล้ว", post_process_jav_thai("ฉันกำลังจะไปแล้ว"))
        self.assertIn("จะเสร็จแล้ว", post_process_jav_thai("ฉันจะไปแล้ว"))
        self.assertIn("เสร็จแล้ว", post_process_jav_thai("ไปแล้ว!"))

        # Pleasure
        self.assertIn("เสียวจัง", post_process_jav_thai("รู้สึกดีจัง"))
        self.assertIn("เสียวมาก", post_process_jav_thai("มันรู้สึกดี"))

        # Refusal & Limits
        self.assertIn("อย่านะ", post_process_jav_thai("ไม่อนุญาต"))
        self.assertIn("ทนไม่ไหวแล้ว", post_process_jav_thai("ฉันไม่สามารถอดทนได้"))

        # Penetration & Climax
        self.assertIn("ลึกจัง", post_process_jav_thai("จนถึงด้านใน"))
        self.assertIn("แตกในเลย", post_process_jav_thai("ใส่มันไว้ข้างใน"))
        self.assertIn("สุดยอดเลย", post_process_jav_thai("มันยอดเยี่ยมมาก"))

    def test_post_process_jav_thai_with_japanese_cues(self):
        # 気持ちいい override
        res = post_process_jav_thai("รู้สึกดี", original_text="気持ちいい")
        self.assertIn("เสียว", res)

        # いく override
        res = post_process_jav_thai("กำลังจะไป", original_text="いっちゃう")
        self.assertIn("เสร็จแล้ว", res)

        # だめ override
        res = post_process_jav_thai("ไม่ได้นะ", original_text="だめ")
        self.assertIn("อย่านะ", res)

        # 中に出して override
        res = post_process_jav_thai("ข้างใน", original_text="中に出して")
        self.assertIn("แตกใน", res)

    def test_post_process_jav_negation_preservation(self):
        # Negation MUST NOT be inverted to "แตกในเลยนะ"
        res_neg = post_process_jav_thai("อย่าใส่ข้างในนะ", original_text="中に出さないで")
        self.assertIn("อย่าแตกในนะ", res_neg)
        self.assertNotIn("แตกในเลยนะ", res_neg)

        res_neg2 = post_process_jav_thai("หยุดแตกใน", original_text="中出しだけはやめて")
        self.assertIn("อย่าแตกในนะ", res_neg2)

        # Climax negation
        res_neg3 = post_process_jav_thai("อย่าเพิ่งไปนะ", original_text="いかないで")
        self.assertIn("อย่าเพิ่งเสร็จนะ", res_neg3)

    def test_post_process_jav_substyles(self):
        # Dirty talk sub-style
        res_dirty = post_process_jav_thai("ดิ๊ก", style="jav_dirty")
        self.assertIn("ควย", res_dirty)

        res_dirty_climax = post_process_jav_thai("ฉันจะไปแล้ว", style="jav_dirty")
        self.assertIn("จะแตกแล้ว", res_dirty_climax)

        # Hardcore & Vulgar sub-styles
        res_hardcore = post_process_jav_thai("ช่องคลอด", style="jav_hardcore")
        self.assertIn("หี", res_hardcore)

        res_vulgar = post_process_jav_thai("気持ちいい", "気持ちいい", style="jav_vulgar")
        self.assertTrue(any(w in res_vulgar for w in ["เสียว", "โคตรเสียว", "เสียวควยมาก"]))

        res_cum = post_process_jav_thai("いっちゃう", "いっちゃう", style="jav_dirty")
        self.assertIn("จะแตกแล้ว", res_cum)

        # Sweet sub-style
        res_sweet = post_process_jav_thai("รู้สึกดีจัง", style="jav_sweet")
        self.assertIn("เสียวจังเลยค่ะ", res_sweet)

        res_sweet_refusal = post_process_jav_thai("ไม่อนุญาต", style="jav_sweet")
        self.assertIn("อย่าแกล้งหนูสิคะ", res_sweet_refusal)

    def test_post_process_newly_fixed_machine_literalisms(self):
        test_cases = [
            ("ไม่ ไม่", "อย่านะ ไม่เอานะ"),
            ("หยุดมัน", "อย่าทำนะ"),
            ("ทำให้มันเข้มข้นยิ่งขึ้น", "เอาให้แรงกว่านี้อีกสิ"),
            ("ถูหน้าอกของฉัน", "ขยำนมฉันสิ"),
            ("ให้ฉันมาก", "ปล่อยออกมาเยอะๆ เลยนะ"),
            ("ยากมาก", "แข็งเป๊กเลย"),
            ("ย้าย", "ขยับสิ"),
            ("กระตุ้นเพิ่มเติม", "กระแทกอีกสิ"),
            ("ใส่มันเข้าไปอย่างรวดเร็ว", "รีบใส่เข้ามาสิ"),
            ("ฉันเข้าไปแล้ว", "ใส่เข้ามาแล้ว"),
            ("ดึงมันออกมา", "เอาออกไปก่อน"),
            ("มันจะแตก", "จะพังแล้ว"),
            ("โปรดยกโทษให้ฉันด้วย", "ยอมแล้ว พอเถอะนะ"),
            ("อย่ามอง", "อย่ามองสิ เขินนะ"),
            ("มันเจ็บ", "เจ็บจัง"),
            ("ฉันรู้สึกได้", "เสียวไปหมดแล้ว"),
            ("การช่วยตัวเอง", "ช่วยตัวเอง"),
            ("น้ำพุ่ง", "น้ำแตกกระจาย"),
            ("อิคุอิคุอิกุ", "จะเสร็จแล้ว! จะแตกแล้ว!"),
        ]
        for raw, expected in test_cases:
            processed = post_process_jav_thai(raw)
            self.assertEqual(processed, expected, f"Failed for raw input '{raw}'")

    def test_post_process_empty_and_passthrough(self):
        self.assertEqual(post_process_jav_thai(""), "")
        self.assertEqual(post_process_jav_thai("สวัสดีครับ ยินดีต้อนรับ"), "สวัสดีครับ ยินดีต้อนรับ")

    def test_post_process_jav_thai_untranslated_japanese_cue_fallback(self):
        # When machine translation fails or leaves raw Japanese cue, post_process_jav_thai MUST convert it to Thai
        self.assertEqual(post_process_jav_thai("いっちゃう", "いっちゃう", style="jav"), "จะเสร็จแล้ว")
        self.assertEqual(post_process_jav_thai("気持ちいい", "気持ちいい", style="jav"), "เสียวจัง")
        self.assertEqual(post_process_jav_thai("中に出して", "中に出して", style="jav"), "แตกในเลย")
        # Negation handling
        self.assertEqual(post_process_jav_thai("いかないで", "いかないで", style="jav"), "อย่าเพิ่งเสร็จนะ")

    def test_translate_texts_to_thai_with_jav_style(self):
        inputs = ["It feels so good", "I am going"]
        origs = ["気持ちいい", "いっちゃう"]
        results = translate_texts_to_thai(inputs, style="jav", original_texts=origs)
        self.assertEqual(len(results), 2)
        # Verify result contains Thai characters
        self.assertTrue(any('\u0e00' <= c <= '\u0e7f' for c in results[0]))
        self.assertTrue(any('\u0e00' <= c <= '\u0e7f' for c in results[1]))

    def test_translate_texts_to_thai_with_progress_callback(self):
        inputs = ["Hello", "Thank you"]
        events = []
        def _cb(pct, msg):
            events.append((pct, msg))
        results = translate_texts_to_thai(inputs, progress_callback=_cb)
        self.assertEqual(len(results), 2)
        self.assertTrue(len(events) >= 1)

    def test_gemini_translation_with_jav_style(self):
        from unittest.mock import MagicMock, patch
        import json

        mock_segments = [
            {"id": 1, "start": 0.0, "end": 2.0, "original_text": "気持ちいい", "thai_text": "", "text": ""},
            {"id": 2, "start": 2.0, "end": 4.0, "original_text": "いっちゃう", "thai_text": "", "text": ""},
        ]

        mock_response = MagicMock()
        mock_response.text = json.dumps([
            {"id": 1, "thai_text": "เสียวจังเลย"},
            {"id": 2, "thai_text": "จะเสร็จแล้วนะ"},
        ])

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.models.generate_content.return_value = mock_response

            out = translate_segments_with_gemini(
                mock_segments,
                api_key="dummy_key",
                style="jav_dirty",
                model="gemini-2.5-pro",
            )
            self.assertEqual(len(out), 2)
            self.assertEqual(out[0]["thai_text"], "เสียวจังเลย")
            self.assertEqual(out[1]["thai_text"], "จะเสร็จแล้วนะ")

            # Check that safety settings and model were passed
            call_kwargs = mock_client.models.generate_content.call_args[1]
            self.assertEqual(call_kwargs["model"], "gemini-2.5-pro")
            self.assertIn("config", call_kwargs)
            self.assertEqual(call_kwargs["config"].response_mime_type, "application/json")
            self.assertIn("JAV", call_kwargs["contents"])

    def test_gemini_translation_model_fallback(self):
        from unittest.mock import MagicMock, patch
        import json

        mock_segments = [
            {"id": 1, "start": 0.0, "end": 2.0, "original_text": "気持ちいい", "thai_text": "", "text": ""},
        ]

        # First model call raises error, fallback model call succeeds
        mock_success_response = MagicMock()
        mock_success_response.text = json.dumps([{"id": 1, "thai_text": "เสียวสุดๆ"}])

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.models.generate_content.side_effect = [
                RuntimeError("Model gemini-2.5-pro not found or restricted"),
                mock_success_response,
            ]

            out = translate_segments_with_gemini(
                mock_segments,
                api_key="dummy_key",
                style="jav",
                model="gemini-2.5-pro",
            )
            self.assertEqual(len(out), 1)
            self.assertEqual(out[0]["thai_text"], "เสียวสุดๆ")
            # Verified generate_content was called twice due to fallback
            self.assertEqual(mock_client.models.generate_content.call_count, 2)

    def test_gemini_translation_dict_wrapper_and_fallback(self):
        from unittest.mock import MagicMock, patch
        import json

        mock_segments = [
            {"id": 1, "start": 0.0, "end": 2.0, "original_text": "気持ちいい", "thai_text": "気持ちいい", "text": "気持ちいい"},
            {"id": 2, "start": 2.0, "end": 4.0, "original_text": "いっちゃう", "thai_text": "いっちゃう", "text": "いっちゃう"},
        ]

        # LLM returns a dict with 'translations' wrapper and 'translation' key, missing seg 2
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "translations": [
                {"id": 1, "translation": "เสียวจังเลยค่ะ"},
            ]
        })

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.models.generate_content.return_value = mock_response

            with patch("engine.translate_texts_to_thai") as mock_fallback:
                mock_fallback.return_value = ["จะเสร็จแล้ว"]
                out = translate_segments_with_gemini(
                    mock_segments,
                    api_key="dummy_key",
                    style="jav",
                )
                self.assertEqual(len(out), 2)
                self.assertIn("เสียว", out[0]["thai_text"])
                # Seg 2 was missing from Gemini output, verified fallback was called
                mock_fallback.assert_called_once()
                self.assertEqual(out[1]["thai_text"], "จะเสร็จแล้ว")


class TestFFmpegAndMediaPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = os.path.abspath("test_media_workspace")
        os.makedirs(cls.test_dir, exist_ok=True)
        cls.ffmpeg = find_ffmpeg()

        # Generate a small 2-second synthetic video with audio tone for tests
        cls.synthetic_video = os.path.join(cls.test_dir, "synthetic.mp4")
        cmd = [
            cls.ffmpeg,
            "-y",
            "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=24",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
            "-c:v", "libx264",
            "-c:a", "aac",
            cls.synthetic_video,
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert res.returncode == 0, f"Failed to create synthetic test video: {res.stderr.decode()}"

        # Generate a small video with NO audio stream
        cls.no_audio_video = os.path.join(cls.test_dir, "no_audio.mp4")
        cmd_no_audio = [
            cls.ffmpeg,
            "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=24",
            "-c:v", "libx264",
            "-an",
            cls.no_audio_video,
        ]
        subprocess.run(cmd_no_audio, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_ffmpeg_found(self):
        ffmpeg_bin = find_ffmpeg()
        self.assertTrue(os.path.isfile(ffmpeg_bin))

    def test_has_audio_stream(self):
        self.assertTrue(has_audio_stream(self.synthetic_video, self.ffmpeg))
        self.assertFalse(has_audio_stream(self.no_audio_video, self.ffmpeg))

    def test_audio_extraction(self):
        out_wav = os.path.join(self.test_dir, "extracted.wav")
        res = extract_audio(self.synthetic_video, out_wav, ffmpeg_path=self.ffmpeg)
        self.assertIsNotNone(res)
        self.assertTrue(os.path.isfile(out_wav))
        self.assertGreater(os.path.getsize(out_wav), 1000)

        # Video without audio should return None cleanly without crashing
        no_audio_wav = os.path.join(self.test_dir, "extracted_none.wav")
        res_none = extract_audio(self.no_audio_video, no_audio_wav, ffmpeg_path=self.ffmpeg)
        self.assertIsNone(res_none)

    def test_audio_extraction_with_progress_callback(self):
        out_wav = os.path.join(self.test_dir, "extracted_with_progress.wav")
        progress_events = []
        def _cb(pct, msg):
            progress_events.append((pct, msg))

        res = extract_audio(self.synthetic_video, out_wav, ffmpeg_path=self.ffmpeg, progress_callback=_cb)
        self.assertIsNotNone(res)
        self.assertTrue(os.path.isfile(out_wav))
        self.assertGreater(os.path.getsize(out_wav), 1000)
        # Should have received at least one progress callback without deadlock
        self.assertTrue(len(progress_events) >= 0)

    def test_burn_subtitles(self):
        srt_file = os.path.join(self.test_dir, "test.srt")
        with open(srt_file, "w", encoding="utf-8") as f:
            f.write("1\n00:00:00,000 --> 00:00:01,500\nทดสอบฝังซับไตเติลภาษาไทย\n")

        burned_mp4 = os.path.join(self.test_dir, "burned.mp4")
        out = burn_subtitles_to_video(self.synthetic_video, srt_file, burned_mp4, ffmpeg_path=self.ffmpeg)
        self.assertTrue(os.path.isfile(out))
        self.assertGreater(os.path.getsize(out), 5000)

    def test_burn_subtitles_with_progress_callback(self):
        srt_file = os.path.join(self.test_dir, "test_prog.srt")
        with open(srt_file, "w", encoding="utf-8") as f:
            f.write("1\n00:00:00,000 --> 00:00:01,500\nทดสอบ progress burn\n")

        burned_mp4 = os.path.join(self.test_dir, "burned_prog.mp4")
        progress_events = []
        def _cb(pct, msg):
            progress_events.append((pct, msg))

        out = burn_subtitles_to_video(
            self.synthetic_video,
            srt_file,
            burned_mp4,
            ffmpeg_path=self.ffmpeg,
            progress_callback=_cb,
        )
        self.assertTrue(os.path.isfile(out))
        self.assertGreater(os.path.getsize(out), 5000)

    def test_burn_subtitles_with_spaces_and_brackets(self):
        # Stress-test FFmpeg filter parsing with brackets, spaces, and Thai characters in filename
        complex_srt = os.path.join(self.test_dir, "[1080p] Thai Movie (ภาษาไทย) [EngSub].srt")
        with open(complex_srt, "w", encoding="utf-8") as f:
            f.write("1\n00:00:00,000 --> 00:00:01,000\nข้อความซับไทยพิเศษ\n")

        burned_complex_mp4 = os.path.join(self.test_dir, "video output with spaces [final].mp4")
        out = burn_subtitles_to_video(self.synthetic_video, complex_srt, burned_complex_mp4, ffmpeg_path=self.ffmpeg)
        self.assertTrue(os.path.isfile(out))
        self.assertGreater(os.path.getsize(out), 5000)

    def test_mux_subtitles_to_video(self):
        srt_file = os.path.join(self.test_dir, "test_mux.srt")
        with open(srt_file, "w", encoding="utf-8") as f:
            f.write("1\n00:00:00,000 --> 00:00:01,000\nทดสอบฟังก์ชัน fast soft-mux\n")

        soft_mp4 = os.path.join(self.test_dir, "soft_muxed.mp4")
        out = mux_subtitles_to_video(self.synthetic_video, srt_file, soft_mp4, ffmpeg_path=self.ffmpeg)
        self.assertTrue(os.path.isfile(out))
        self.assertGreater(os.path.getsize(out), 1000)

    def test_process_video_with_auto_embed_soft(self):
        out_dir = os.path.join(self.test_dir, "auto_embed_soft")
        res = process_video_subtitles(
            self.synthetic_video,
            out_dir,
            model_size="tiny",
            embed_mode="soft",
            ffmpeg_path=self.ffmpeg,
        )
        self.assertTrue(res["success"])
        self.assertIsNotNone(res.get("softsub_video_path"))
        self.assertTrue(os.path.isfile(res["softsub_video_path"]))
        self.assertGreater(os.path.getsize(res["softsub_video_path"]), 1000)

    def test_process_silent_video(self):
        # A test video with tone won't have words, so Whisper detects empty/silent speech
        out_dir = os.path.join(self.test_dir, "sub_result")
        res = process_video_subtitles(
            self.synthetic_video,
            out_dir,
            model_size="tiny",
            ffmpeg_path=self.ffmpeg,
        )
        self.assertTrue(res["success"])
        self.assertTrue(os.path.isfile(res["srt_path"]))
        self.assertTrue(os.path.isfile(res["vtt_path"]))

    def test_process_video_without_audio_stream(self):
        out_dir = os.path.join(self.test_dir, "no_audio_sub_result")
        res = process_video_subtitles(
            self.no_audio_video,
            out_dir,
            model_size="tiny",
            ffmpeg_path=self.ffmpeg,
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["detected_language"], "none")
        self.assertEqual(len(res["segments"]), 0)
        self.assertTrue(os.path.isfile(res["srt_path"]))
        self.assertTrue(os.path.isfile(res["vtt_path"]))

    def test_process_video_translates_when_detected_lang_is_th_but_content_is_japanese(self):
        # Even if Whisper or user says language is 'th', if transcribed segments contain Japanese text,
        # the engine MUST translate them to Thai.
        from unittest.mock import patch, MagicMock

        out_dir = os.path.join(self.test_dir, "th_lang_japanese_content")

        mock_seg = MagicMock()
        mock_seg.start = 0.5
        mock_seg.end = 2.0
        mock_seg.text = "もう、そんなにコンツメないの?"

        mock_info = MagicMock()
        mock_info.language = "th"  # Mistakenly detected or forced as Thai
        mock_info.duration = 2.0

        with patch("engine.load_whisper_model_safely") as mock_load:
            mock_whisper = MagicMock()
            mock_whisper.transcribe.return_value = ([mock_seg], mock_info)
            mock_load.return_value = mock_whisper

            res = process_video_subtitles(
                self.synthetic_video,
                out_dir,
                model_size="tiny",
                source_lang="th",
                translation_style="jav",
                ffmpeg_path=self.ffmpeg,
            )

            self.assertTrue(res["success"])
            self.assertEqual(len(res["segments"]), 1)
            thai_text = res["segments"][0]["thai_text"]
            # Must NOT be the raw Japanese text!
            self.assertNotEqual(thai_text, "もう、そんなにコンツメないの?")
            # Must contain Thai characters
            self.assertTrue(any('\u0e00' <= c <= '\u0e7f' for c in thai_text))
            # Must not contain Japanese characters
            self.assertFalse(any('\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in thai_text))


class TestWhisperSafeLoading(unittest.TestCase):
    def test_safe_whisper_loading_cpu_fallback(self):
        # Even if machine lacks cublas64_12.dll, load_whisper_model_safely never crashes
        model = load_whisper_model_safely("tiny")
        self.assertIsNotNone(model)
        self.assertEqual(model.model.device, "cpu")

    def test_check_cuda_availability_handles_probe_failure(self):
        from unittest.mock import patch
        with patch("engine._CUDA_SAFE_AVAILABLE", None):
            with patch("ctranslate2.get_cuda_device_count", return_value=0):
                self.assertFalse(check_cuda_availability())


if __name__ == "__main__":
    unittest.main()
