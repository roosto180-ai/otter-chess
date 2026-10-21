import tempfile,unittest
from pathlib import Path
import fastchess,pyarrow as pa,pyarrow.parquet as pq,torch
from data_loader import OtterGameParquetStream,StreamConfig,auxiliary_target,elo_to_bucket,time_control_to_bucket

class FineTuneDataTests(unittest.TestCase):
    def test_subsampling_retains_position_and_complete_history(self):
        moves='e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Be7 Re1 b5 Bb3 d6 c3 O-O h3 Nb8 d4 Nbd7 c4 c6 Nc3 Qc7 Be3 Bb7 Rc1 Rfe8 a3 Bf8'
        with tempfile.TemporaryDirectory(prefix='otter-test-') as directory:
            path=Path(directory)/'month=train'/'elo_band=4'; path.mkdir(parents=True)
            row=dict(month='train',elo_band=4,result='1/2-1/2',white_elo=1700,black_elo=1800,time_control='180+0',moves_san=moves,
                     move_clocks='|'.join(['0:03:00']*len(moves.split())),source_id='https://example.invalid/game')
            pq.write_table(pa.Table.from_pylist([row]),path/'part-000000.parquet')
            full=list(OtterGameParquetStream(StreamConfig(data_dir=directory,months=['train'])))
            sampled=list(OtterGameParquetStream(StreamConfig(data_dir=directory,months=['train'],positions_per_game=8)))
            self.assertEqual(len(sampled),8)
            for sample in sampled:
                expected=full[sample['ply_index']]
                for key in ('board','history_ids','history_mask','aux_target','clock_features','legal_move_mask'):
                    torch.testing.assert_close(sample[key],expected[key])
                self.assertEqual(sample['target_move_id'],expected['target_move_id'])
                self.assertTrue(sample['legal_move_mask'][sample['target_move_id']])

    def test_white_auxiliary_target_uses_pre_move_board(self):
        board=fastchess.Board(); before=board.copy(); board.push_san('e4')
        target=auxiliary_target(before,'e2e4')
        self.assertEqual(target[0].item(),1)
        self.assertEqual(target[13+12].item(),1)
        self.assertEqual(target[77+28].item(),1)
        self.assertEqual(before.fen(),fastchess.Board().fen())

    def test_original_conditioning_buckets(self):
        self.assertEqual(time_control_to_bucket('180+0'),2)
        self.assertEqual({elo_to_bucket(e) for e in range(600,3201)},set(range(11)))

if __name__=='__main__': unittest.main()
