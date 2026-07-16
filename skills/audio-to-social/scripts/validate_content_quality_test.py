import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("validate_content_quality.py")

_spec = importlib.util.spec_from_file_location("audio_to_social_quality_validator", SCRIPT_PATH)
_module = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules[_spec.name] = _module
_spec.loader.exec_module(_module)

validate_project = _module.validate_project


# A clean, valid boker (podcast) script body: pure prose, no markdown markers
# (#/**/>), no banned AI phrases, every paragraph <=80 visible chars, and long
# enough to clear the 1550-char floor. Shared by the boker happy-path tests.
_VALID_BOKER_PARAGRAPHS = [
    "作者花了三小时排查一个自动化流程问题，最后发现真正卡住的是流程本身。",
    "排查过程中反复检查工具链，每个工具单独跑都没问题，但串起来就断。",
    "问题出在一个中间环节的超时设置上，默认值太短，导致长任务中途失败。",
    "后来把流程拆成可续跑阶段，每个阶段独立记录状态，失败后不用从头再来。",
    "这种设计思路其实不新鲜，但在个人自动化工具里经常被忽略。",
    "可续跑的本质是把状态持久化，让每一步都能独立重试。",
    "这次录音也被整理成社交平台内容，顺手验证这套流程是否稳定。",
    "从实际效果看，拆分后的流程运行了二十多次都没有出现中途卡住的情况。",
    "个人做自动化工具时，流程稳定性比工具功能本身更重要。",
    "如果流程经常断，再好的工具也没法持续产出价值。",
    "建议大家在设计自动化流程时，第一步就把可续跑考虑进去。",
    "不要等到流程出问题了再回头改，那时候已经浪费了大量时间。",
    "这次踩坑的教训是：先把流程设计好，再往里面填工具。",
    "工具可以随时换，但流程一旦跑起来，改动的代价就大多了。",
    "希望这次复盘能帮到同样在做个人自动化工具的朋友们。",
    "你们做自动化时，会先修工具，还是先修流程？欢迎分享经验。",
    "另外一个容易被忽视的点是日志和监控，没有日志排查就像盲人摸象。",
    "我在每个阶段都加了简单的状态记录，出了问题直接看日志就行。",
    "这也算是可续跑设计的一个副产品，状态记录本身就是最好的日志。",
    "个人工具不需要企业级的监控系统，但至少要能回答哪一步出了错。",
    "推荐的做法是在每个阶段结束时写入一行状态到文件里。",
    "格式可以很简单，比如时间戳加阶段名加结果就行了。",
    "有了这些记录，下次出问题就可以直接定位到具体的阶段。",
    "还有一个实用的建议是把超时时间设置得宽松一些。",
    "个人工具不像线上服务需要毫秒级响应，多等几秒完全没问题。",
    "这次踩坑让我重新审视了自己所有的自动化流程。",
    "发现还有好几个地方也存在类似的隐患，趁这次一起修了。",
    "总结下来，设计自动化流程的三个原则是：可续跑、有日志、超时宽松。",
    "这三点做好了，大部分流程问题都可以快速定位和修复。",
    "希望这些经验对你们有帮助，也欢迎分享你们在自动化方面的心得。",
    "每次踩坑后做一次简单复盘，把经验沉淀下来，就能避免重复犯错。",
    "好了，今天的分享就到这里，感谢大家的收听。",
    "对了，还有一个小技巧：给流程加上版本号。",
    "每次修改流程时更新版本号，这样出问题时可以快速判断是哪个版本引入的。",
    "版本号不需要很复杂，简单递增的数字就够了。",
    "我还建了一个简单的变更日志，记录每次改了什么、为什么改。",
    "这些习惯看起来是额外工作量，但长远来看节省的时间远超投入。",
    "尤其是在流程复杂起来之后，没有记录的话自己都忘了当时为什么这么设计。",
    "所以我的建议是：从第一个版本开始就记录变更。",
    "这样半年后回头看，还能清楚地知道每个设计决策的背景。",
    "好了，这次真的结束了，祝大家的自动化流程都稳如磐石。",
    "如果你们也在做类似的内容创作自动化工具，欢迎多交流。",
    "非常推荐先把核心流程跑通，再逐步加平台适配。",
    "不要一开始就想着同时支持四五个平台，那样只会增加复杂度。",
    "先做好一个平台，确认流程稳定后再扩展到其他平台。",
    "这种渐进式的开发方式在个人项目里特别有效，避免了过度设计。",
    "好了，这次是真正的最后一句了，我们下期再见。",
    "顺便提一下，很多朋友问我用什么工具来管理这些自动化流程。",
    "其实我用的就是最简单的文件系统加上几个 Python 脚本。",
    "不需要什么复杂的流程引擎，文件和目录就是最好的状态存储。",
    "每个项目一个目录，每个阶段一个文件，简单明了。",
    "如果以后流程复杂了，再考虑引入更正式的方案也不迟。",
    "今天就到这里吧，真的结束了，感谢大家的收听和支持。",
]


def _write_valid_boker(output_dir: Path) -> None:
    """Write a boker script + meta that satisfy every machine quality gate."""
    import re as _re

    script_body = "\n\n".join(_VALID_BOKER_PARAGRAPHS)
    # Guarantee we clear the 1550-char floor with margin, regardless of how the
    # paragraph list above is edited. Each iteration adds ~50 clean visible chars.
    while len(_re.sub(r"\s+", "", script_body)) < 1700:
        script_body += (
            "\n\n以上就是这次自动化流程踩坑复盘的全部内容，希望对你有启发。"
            "\n\n记住三个关键点：可续跑设计、完善的日志记录、宽松的超时设置。"
        )
    (output_dir / "播客_脚本.txt").write_text(script_body, encoding="utf-8")
    # Title must start with a 4-digit zero-padded episode number + fullwidth colon.
    (output_dir / "播客_标题与描述.txt").write_text(
        "标题：0224：流程坏了比工具坏了更难发现\n"
        "简介：一次三小时排查自动化流程问题的复盘\n"
        "标签：#AI自动化 #个人项目 #流程设计 #踩坑复盘 #自动化工具 #可续跑",
        encoding="utf-8",
    )


class AudioToSocialQualityValidatorTests(unittest.TestCase):
    def test_quick_mode_still_blocks_banned_ai_phrase(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            (output_dir / "公众号_文章.md").write_text(
                "# 三小时排查后我发现坏掉的不是工具\n\n"
                "值得一提，作者花了三小时排查一个自动化流程问题。\n",
                encoding="utf-8",
            )
            (output_dir / "公众号_摘要.txt").write_text("一次自动化流程复盘", encoding="utf-8")

            result = validate_project(output_dir, ["gongzhonghao"])

            self.assertFalse(result.passed)
            self.assertIn("banned_phrase", result.failures_by_platform["gongzhonghao"][0].code)

    def test_banned_start_phrase_without_trailing_punctuation_is_flagged(self) -> None:
        """最后 at paragraph start is flagged even with no punctuation after it.

        Regression for the over-tight ``[，,：:]`` anchor that let
        '最后我们来看看…' slip through. brand-config bans 最后 as a paragraph
        opener regardless of what follows.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            (output_dir / "公众号_文章.md").write_text(
                "# 这是一个十五到三十字之间的合法标题\n\n"
                "正文段落，没有任何问题，就是普通的叙述内容。\n\n"
                "最后我们来看看这次踩坑带来了哪些启发。\n",
                encoding="utf-8",
            )
            (output_dir / "公众号_摘要.txt").write_text("一次踩坑复盘", encoding="utf-8")

            result = validate_project(output_dir, ["gongzhonghao"])

            self.assertFalse(result.passed)
            codes = [f.code for f in result.failures_by_platform["gongzhonghao"]]
            self.assertIn("platform.banned_phrase", codes)

    def test_v3_state_without_phase3_tracks_passes(self) -> None:
        """v3.1 state.json (phase3 has only `status`, no per-platform tracks) must NOT trip STATE_SCHEMA.

        Regression guard for the removed phase3.tracks check.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            state = {
                "schema_version": "audio-to-social-v3",
                "output_dir": str(output_dir),
                "requested_platforms": ["boker"],
                "phase3": {"status": "completed"},  # no `tracks` sub-object
            }
            (output_dir / "state.json").write_text(
                json.dumps(state, ensure_ascii=False), encoding="utf-8"
            )
            _write_valid_boker(output_dir)

            result = validate_project(output_dir, ["boker"])

            self.assertTrue(result.passed, result.to_dict())
            self.assertEqual(
                [f for f in result.global_failures if f.code == "STATE_SCHEMA"],
                [],
            )

    def test_valid_boker_content_passes_machine_checks(self) -> None:
        """Boker (podcast) content should pass machine validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            _write_valid_boker(output_dir)

            result = validate_project(output_dir, ["boker"])

            self.assertTrue(result.passed, result.to_dict())


if __name__ == "__main__":
    unittest.main()
