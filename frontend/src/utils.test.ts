import {describe,it,expect} from 'vitest';
import {clock,hpPercent,clamp} from './utils';
describe('display preserves zero vs unavailable',()=>{
 it('renders actual game time',()=>{expect(clock(null)).toBe('—');expect(clock(0)).toBe('00:00');expect(clock(7380)).toBe('02:03')});
 it('keeps health within the track',()=>{expect(hpPercent(0,20)).toBe(0);expect(hpPercent(10,20)).toBe(50);expect(hpPercent(30,20)).toBe(100);expect(hpPercent(2,0)).toBe(0)});
 it('keeps dragged components on the canvas',()=>{expect(clamp(-50,0,100)).toBe(0);expect(clamp(500,0,100)).toBe(100)});
});
