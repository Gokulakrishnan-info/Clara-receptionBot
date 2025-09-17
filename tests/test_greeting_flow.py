import asyncio

# End-to-end-ish test that simulates: wake word -> recognition -> greeting,
# then queries company info. It avoids camera/thread by stubbing service start.


class DummyLogger:
    def __init__(self):
        self.messages = []

    def info(self, msg: str):
        self.messages.append(str(msg))


class DummyContext:
    def __init__(self):
        self.logger = DummyLogger()


def test_face_greeting_and_company_info(monkeypatch):
    import face_recognition.face_integration as fi
    from Modules.company_info import company_info

    # 1) Bypass wake word
    monkeypatch.setattr(fi, "wait_for_wakeword", lambda phrase="hey clara": None)

    # 2) Avoid constructing real service/recognizer by injecting a singleton
    class FakeService:
        def start(self, on_greet, on_prompt=None):
            on_greet({"EmployeeID": "E001", "Name": "Alice"})
    fi.service_singleton = FakeService()

    # 3) Run the start_face_greeting tool and capture LiveKit log output
    ctx = DummyContext()
    asyncio.run(fi.start_face_greeting(ctx, embeddings_path="ignored", threshold=0.0))

    # Assert greeting went through LiveKit logging
    joined = "\n".join(ctx.logger.messages)
    assert "Welcome back, Alice" in joined

    # 4) Now simulate the next step in the conversation: ask for company info
    # This calls the actual async tool and ensures it returns a string.
    # We do not validate content as it depends on the PDF; only that it responds.
    result = asyncio.run(company_info(ctx, "general"))
    assert isinstance(result, str)
    assert len(result) > 0


