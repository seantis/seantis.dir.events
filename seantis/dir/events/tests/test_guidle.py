import pytz

from datetime import datetime

from seantis.dir.events.tests import IntegrationTestCase
from seantis.dir.events.sources import guidle


class TestGuidleSource(IntegrationTestCase):

    def test_parsers(self):

        minutes = 60
        offset = guidle.parse_offset

        self.assertEqual(offset('+01:00'), 60 * minutes)
        self.assertEqual(offset('-01:00'), -60 * minutes)
        self.assertEqual(offset('+1:30'), 90 * minutes)
        self.assertEqual(offset(''), 0)
        self.assertRaises(AssertionError, offset, '01:00')
        self.assertRaises(AssertionError, offset, '01:00')

        date = guidle.parse_date
        self.assertEqual(date('2012-12-01+01:00'),
            datetime(2012, 11, 30, 23, 0, tzinfo=pytz.timezone('UTC'))
        )
        self.assertEqual(
            date('2012-12-01+01:00').astimezone(
                pytz.timezone('Europe/Zurich')
            ),
            datetime(2012, 12, 01, 0, 0, tzinfo=pytz.timezone('Europe/Zurich'))
        )
        self.assertEqual(
            date('2012-12-01'),
            datetime(2012, 12, 01, 0, 0, tzinfo=pytz.timezone('UTC'))
        )

        time = guidle.parse_time
        self.assertEqual(time('12:00+01:00'), (12, 0, 60 * minutes))
        self.assertEqual(time('12:00:00.123-01:00'), (12, 0, -60 * minutes))
        self.assertEqual(time('09:13:00.123-02:00'), (9, 13, -120 * minutes))

        apply_time = guidle.apply_time
        self.assertEqual(apply_time(date('2012-12-01+01:00'), '12:00+01:00'),
            datetime(2012, 12, 01, 11, 0, tzinfo=pytz.timezone('UTC'))
        )

        self.assertEqual(
            apply_time(date('2012-12-01+01:00'), '12:00+01:00').astimezone(
                pytz.timezone('Europe/Zurich')
            ),
            datetime(2012, 12, 01, 12, 0, tzinfo=pytz.timezone(
                'Europe/Zurich'
            ))
        )
