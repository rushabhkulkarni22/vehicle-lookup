import contextlib
import io
import unittest
from unittest.mock import patch
import find_vehicle_iphone as app


class ConsoleTests(unittest.TestCase):
    def run_console(self, inputs, result=None, error=None):
        output = io.StringIO()
        with patch('builtins.input', side_effect=inputs), patch.object(app, 'lookup', return_value=result, side_effect=error) as lookup, contextlib.redirect_stdout(output):
            app.main()
        return output.getvalue(), lookup

    def test_invalid_input_and_quit(self):
        output, lookup = self.run_console(['', '../../login', 'q'])
        lookup.assert_not_called()
        self.assertIn('Enter an Indian registration', output)
        self.assertIn('Finished.', output)

    def test_success_then_quit(self):
        result = app.parse_page('<p>MH12XQ4561</p><b>Make &amp; Model</b><i>Example Car</i><b>Owner Name</b><i>A*** B***</i>', 'MH12XQ4561')
        output, lookup = self.run_console(['mh12 xq-4561', 'quit'], result=result)
        lookup.assert_called_once_with('MH12XQ4561')
        self.assertIn('Make & Model: Example Car', output)
        self.assertIn('Owner (masked): A*** B***', output)

    def test_blocked_request_returns_to_prompt(self):
        output, lookup = self.run_console(['MH12XQ4561', 'exit'], error=app.LookupError('CarInfo blocked automated access.'))
        self.assertIn('Lookup unavailable:', output)
        self.assertIn('Safari', output)
        lookup.assert_called_once()

    def test_eof_and_cancel_exit_cleanly(self):
        for exception in (EOFError, KeyboardInterrupt):
            output, _ = self.run_console([exception])
            self.assertIn('Finished.', output)

    def test_full_and_hidden_names_withheld(self):
        html = '<p>MH12XQ4561</p><b>Make &amp; Model</b><i>Example Car</i><div hidden><b>Owner Name</b><i>A*** B***</i></div><b>Owner Name</b><i>Example Person</i>'
        self.assertIsNone(app.parse_page(html, 'MH12XQ4561')['owner_name_masked'])


if __name__ == '__main__':
    unittest.main()
